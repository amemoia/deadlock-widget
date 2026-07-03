from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .consts import TESSERACT_DIR_DEFAULT

try:
    import pytesseract
except ImportError:
    pytesseract = None

@dataclass(slots=True)
class Box:
    left: float
    top: float
    width: float
    height: float

    def to_pixels(self, image_width: int, image_height: int) -> tuple[int, int, int, int]:
        left = max(0, min(image_width, int(round(image_width * self.left))))
        top = max(0, min(image_height, int(round(image_height * self.top))))
        right = max(left + 1, min(image_width, int(round(image_width * (self.left + self.width)))))
        bottom = max(top + 1, min(image_height, int(round(image_height * (self.top + self.height)))))
        return left, top, right, bottom

REGION_BOXES: dict[str, Box] = {
    "nickname": Box(0.1, 0.0725, 0.15, 0.04),
    "top_hero": Box(0.3, 0.375, 0.1075, 0.1),
    "games_played": Box(0.42, 0.485, 0.09, 0.0575),
    "games_won": Box(0.51, 0.485, 0.09, 0.0575),
    "denies": Box(0.51, 0.5925, 0.09, 0.0575),
    "commends": Box(0.42, 0.70, 0.09, 0.05),
    "kills": Box(0.63, 0.475, 0.070, 0.05),
    "assists": Box(0.7125, 0.475, 0.075, 0.05),
}

@dataclass(slots=True)
class OcrWord:
    text: str
    left: int
    top: int
    right: int
    bottom: int
    confidence: float

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def center_x(self) -> float:
        return (self.left + self.right) / 2


@dataclass(slots=True)
class ProfileOcr:
    nickname: list[OcrWord]
    top_hero: list[OcrWord]
    stats: dict[str, list[OcrWord]]



def run_ocr(image_path: Path) -> ProfileOcr:
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image).convert("RGB")

    if not _can_use_tesseract():
        raise RuntimeError("Tesseract is required for OCR but could not be configured.")

    image_width, image_height = image.size
    stat_names = ("games_played", "games_won", "commends", "kills", "assists", "denies")
    stats = {
        key: _ocr_stat_region(image, _box_for(key), image_width, image_height)
        for key in stat_names
    }

    return ProfileOcr(
        nickname=_ocr_region(image, _box_for("nickname"), image_width, image_height),
        top_hero=_ocr_hero_region(image, image_width, image_height),
        stats=stats,
    )


def save_region_debug_image(image_path: Path, output_path: Path | None = None) -> Path:
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()

    colors = [
        (255, 92, 92, 255),
        (92, 168, 255, 255),
        (92, 214, 125, 255),
        (255, 196, 92, 255),
        (198, 92, 255, 255),
        (92, 255, 229, 255),
        (255, 92, 170, 255),
        (255, 140, 92, 255),
    ]

    for index, (name, box) in enumerate(REGION_BOXES.items()):
        color = colors[index % len(colors)]
        left, top, right, bottom = box.to_pixels(*image.size)
        draw.rectangle((left, top, right, bottom), outline=color, width=max(3, image.width // 500))

        label = f"{name} {left},{top}-{right},{bottom}"
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = max(0, min(image.width - text_width - 8, left))
        text_y = max(0, top - text_height - 6)
        draw.rounded_rectangle(
            (text_x - 4, text_y - 2, text_x + text_width + 4, text_y + text_height + 2),
            radius=4,
            fill=(0, 0, 0, 180),
        )
        draw.text((text_x, text_y), label, fill=color, font=font)

    annotated = Image.alpha_composite(image, overlay).convert("RGB")
    target_path = output_path or Path(__file__).resolve().parent.parent / f"{image_path.stem}.regions.png"
    annotated.save(target_path)
    return target_path


def save_region_debug_crops(image_path: Path, output_dir: Path | None = None) -> Path:
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image).convert("RGB")

    target_dir = output_dir or Path(__file__).resolve().parent.parent / "debug"
    target_dir.mkdir(parents=True, exist_ok=True)

    image_width, image_height = image.size
    for name, box in REGION_BOXES.items():
        left, top, right, bottom = box.to_pixels(image_width, image_height)
        crop = image.crop((left, top, right, bottom))
        crop.save(target_dir / f"{name}.png")

    return target_dir


def _ocr_region(image: Image.Image, box: Box, image_width: int, image_height: int) -> list[OcrWord]:
    left, top, right, bottom = box.to_pixels(image_width, image_height)
    crop = image.crop((left, top, right, bottom))
    return _tesseract_words(crop, offset=(left, top))


def _ocr_stat_region(image: Image.Image, box: Box, image_width: int, image_height: int) -> list[OcrWord]:
    left, top, right, bottom = box.to_pixels(image_width, image_height)
    crop = image.crop((left, top, right, bottom))
    value_crop = crop

    candidates = [
        _tesseract_words(value_crop, offset=(left, top)),
        _tesseract_words(_prepare_stat_image(value_crop, scale=2, invert=False), offset=(left, top)),
        _tesseract_words(_prepare_stat_image(value_crop, scale=2, invert=True), offset=(left, top)),
    ]

    return max(candidates, key=_numeric_score)


def _ocr_hero_region(image: Image.Image, image_width: int, image_height: int) -> list[OcrWord]:
    left, top, right, bottom = _box_for("top_hero").to_pixels(image_width, image_height)
    crop = image.crop((left, top, right, bottom))
    band_top, band_bottom = _find_highlight_band(crop)
    focused = crop.crop((0, band_top, crop.width, band_bottom))
    words = _tesseract_words(focused, offset=(left, top + band_top))
    if words:
        return words
    return _tesseract_words(crop, offset=(left, top))


def _can_use_tesseract() -> bool:
    if pytesseract is None:
        return False

    tesseract_on_path = shutil.which("tesseract")
    if tesseract_on_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_on_path
        return True

    tesseract_exe = get_tesseract_exe()
    if tesseract_exe is None or not tesseract_exe.exists():
        return False

    pytesseract.pytesseract.tesseract_cmd = str(tesseract_exe)
    return True


def get_tesseract_dir() -> Path | None:
    configured = os.environ.get("TESSERACT_DIR")
    if configured is None:
        return TESSERACT_DIR_DEFAULT

    cleaned = configured.strip().strip('"')
    return Path(cleaned)


def get_tesseract_exe() -> Path | None:
    directory = get_tesseract_dir()
    if directory is None:
        return None

    return directory / "tesseract.exe"


def _tesseract_words(image: Image.Image, offset: tuple[int, int]) -> list[OcrWord]:
    if pytesseract is None:
        raise RuntimeError("pytesseract is not installed.")

    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    words: list[OcrWord] = []
    for index, text in enumerate(data["text"]):
        cleaned = str(text).strip()
        if not cleaned:
            continue

        confidence_text = str(data["conf"][index]).strip()
        confidence = float(confidence_text) if confidence_text not in {"", "-1"} else -1.0
        left = int(data["left"][index]) + offset[0]
        top = int(data["top"][index]) + offset[1]
        width = int(data["width"][index])
        height = int(data["height"][index])

        words.append(
            OcrWord(
                text=cleaned,
                left=left,
                top=top,
                right=left + width,
                bottom=top + height,
                confidence=confidence,
            )
        )

    return words




def _prepare_stat_image(image: Image.Image, scale: int, invert: bool) -> Image.Image:
    prepared = ImageOps.grayscale(image)
    prepared = ImageOps.autocontrast(prepared)

    if invert:
        prepared = ImageOps.invert(prepared)

    if scale > 1:
        prepared = prepared.resize((prepared.width * scale, prepared.height * scale), Image.Resampling.LANCZOS)

    return prepared


def _numeric_score(words: list[OcrWord]) -> tuple[int, float, int]:
    digit_count = sum(len(re.findall(r"\d", word.text)) for word in words)
    confidence_total = sum(word.confidence for word in words)
    return digit_count, confidence_total, len(words)


def _find_highlight_band(image: Image.Image) -> tuple[int, int]:
    if image.height <= 1:
        return 0, image.height

    slim = image.resize((1, image.height))
    start = int(image.height * 0.12)
    end = max(start + 1, int(image.height * 0.9))
    best_score = None
    best_y = image.height // 2

    for y in range(start, end):
        red, green, blue = slim.getpixel((0, y))
        score = (red * 1.6) + (green * 2.0) - (blue * 0.6)
        if best_score is None or score > best_score:
            best_score = score
            best_y = y

    band_height = max(40, int(image.height * 0.14))
    top = max(0, best_y - band_height // 2)
    bottom = min(image.height, top + band_height)
    return top, bottom

def _box_for(name: str) -> Box:
    return REGION_BOXES[name]


def group_words_into_lines(words: list[OcrWord]) -> list[list[OcrWord]]:
    ordered_words = sorted(words, key=lambda word: (word.center_y, word.left))
    if not ordered_words:
        return []

    lines: list[list[OcrWord]] = []
    current_line: list[OcrWord] = [ordered_words[0]]
    current_center = ordered_words[0].center_y
    current_height = max(1.0, float(ordered_words[0].height))

    for word in ordered_words[1:]:
        line_threshold = max(12.0, current_height * 0.7)
        if abs(word.center_y - current_center) <= line_threshold:
            current_line.append(word)
            current_center = (current_center * (len(current_line) - 1) + word.center_y) / len(current_line)
            current_height = max(current_height, float(word.height))
            continue

        lines.append(sorted(current_line, key=lambda item: item.left))
        current_line = [word]
        current_center = word.center_y
        current_height = max(1.0, float(word.height))

    lines.append(sorted(current_line, key=lambda item: item.left))
    return lines


def line_text(line: list[OcrWord]) -> str:
    return " ".join(word.text for word in sorted(line, key=lambda item: item.left))