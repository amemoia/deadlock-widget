from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import pytesseract
from PIL import Image, ImageOps
from rapidocr_onnxruntime import RapidOCR

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


def run_ocr(image_path: Path, backend: str = "auto") -> list[OcrWord]:
    if backend not in {"auto", "rapidocr", "pytesseract"}:
        raise ValueError("backend must be one of: auto, rapidocr, pytesseract")

    if backend in {"auto", "rapidocr"}:
        try:
            return _rapidocr_words(image_path)
        except Exception:
            if backend == "rapidocr":
                raise

    return _pytesseract_words(image_path)


def _rapidocr_words(image_path: Path) -> list[OcrWord]:
    engine = RapidOCR()
    result = engine(str(image_path))
    if not result:
        return []

    detections = result[0] if isinstance(result, tuple) else result
    words: list[OcrWord] = []
    for item in detections or []:
        if len(item) < 3:
            continue
        box, text, score = item[:3]
        if not text:
            continue
        points = list(box)
        xs = [int(point[0]) for point in points]
        ys = [int(point[1]) for point in points]
        words.append(
            OcrWord(
                text=str(text).strip(),
                left=min(xs),
                top=min(ys),
                right=max(xs),
                bottom=max(ys),
                confidence=float(score),
            )
        )
    return words


def _pytesseract_words(image_path: Path) -> list[OcrWord]:
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    words: list[OcrWord] = []
    for index, text in enumerate(data["text"]):
        cleaned = str(text).strip()
        if not cleaned:
            continue
        confidence = float(data["conf"][index]) if str(data["conf"][index]).strip() not in {"", "-1"} else -1.0
        left = int(data["left"][index])
        top = int(data["top"][index])
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


def group_words_into_lines(words: Iterable[OcrWord]) -> list[list[OcrWord]]:
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


def line_text(line: Iterable[OcrWord]) -> str:
    return " ".join(word.text for word in sorted(line, key=lambda item: item.left))