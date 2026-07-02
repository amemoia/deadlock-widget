from __future__ import annotations
import re
from dataclasses import dataclass

from .models import DeadlockProfile, DeadlockStats
from .ocr import OcrWord, group_words_into_lines, line_text
from .consts import STAT_LABELS, NUMBER_PATTERN, EXCLUDES, DEFAULT_IMAGES_URL

def parse_deadlock_stats(words: list[OcrWord]) -> DeadlockStats:
    found = _extract_stats_from_layout(words)
    if len(found) < len(STAT_LABELS):
        for line in group_words_into_lines(words):
            text = line_text(line)
            for key, label in STAT_LABELS:
                if key not in found:
                    match = _find_stat_value(text, label)
                    if match is not None:
                        found[key] = match

    missing = [name for name, _ in STAT_LABELS if name not in found]
    if missing:
        raise ValueError(f"Could not extract from OCR output: {', '.join(missing)}")

    return DeadlockStats(
        games_played=found["games_played"],
        games_won=found["games_won"],
        commends=found["commends"],
        kills=found["kills"],
        assists=found["assists"],
        denies=found["denies"],
    )


def parse_deadlock_profile(words: list[OcrWord], hero_image_base_url: str = DEFAULT_IMAGES_URL) -> DeadlockProfile:
    stats = parse_deadlock_stats(words)
    nickname = extract_nickname(words)
    top_hero = extract_top_hero(words)
    hero_image_url = build_hero_image_url(top_hero, hero_image_base_url) if top_hero else None
    hero_card_url = build_hero_card_url(top_hero, hero_image_base_url) if top_hero else None

    return DeadlockProfile(
        username=nickname or "",
        stats=stats,
        nickname=nickname,
        top_hero=top_hero,
        hero_image_url=hero_image_url,
        hero_card_url=hero_card_url,
    )


def extract_nickname(words: list[OcrWord]) -> str | None:
    region_words = [
        word
        for word in words
        if 180 <= word.left <= 450 and 70 <= word.top <= 88
    ]
    lines = group_words_into_lines(region_words)
    candidates: list[tuple[float, int, str]] = []
    for line in lines:
        text = line_text(line).strip()
        if not _looks_like_profile_text(text):
            continue
        if any(char.isdigit() for char in text):
            continue
        left = min(word.left for word in line)
        top = min(word.top for word in line)
        if _is_excluded_profile_phrase(text):
            continue
        word_count = len(text.split())
        if word_count < 1 or word_count > 3:
            continue
        candidates.append((top, -len(text), text))

    if not candidates:
        return None

    return min(candidates)[2]


def extract_top_hero(words: list[OcrWord]) -> str | None:
    lines = group_words_into_lines(words)
    candidates: list[tuple[float, int, str]] = []
    for line in lines:
        text = line_text(line).strip()
        if not _looks_like_profile_text(text):
            continue
        if any(char.isdigit() for char in text):
            continue
        left = min(word.left for word in line)
        top = min(word.top for word in line)
        if left < 480 or left > 930 or top < 320:
            continue
        if _is_excluded_profile_phrase(text):
            continue
        if len(text.split()) > 2:
            continue
        candidates.append((top, len(text.split()), text))

    if not candidates:
        return None

    return min(candidates)[2]


def build_hero_image_url(hero_name: str, base_url: str = DEFAULT_IMAGES_URL) -> str:
    normalized_base = _normalize_hero_base_url(base_url)
    filename = re.sub(r"\s+", "_", hero_name.strip())
    return f"{normalized_base}/{filename}_Render.png"


def build_hero_card_url(hero_name: str, base_url: str = DEFAULT_IMAGES_URL) -> str:
    normalized_base = _normalize_hero_base_url(base_url)
    filename = re.sub(r"\s+", "_", hero_name.strip())
    return f"{normalized_base}/{filename}_card.png"


def _normalize_hero_base_url(base_url: str) -> str:
    normalized_base = base_url.rstrip("/")
    return normalized_base.replace("/refs/heads/", "/")


def _extract_stats_from_layout(words: list[OcrWord]) -> dict[str, int]:
    found: dict[str, int] = {}
    number_words = [word for word in words if _looks_like_number_word(word.text)]

    for key, label in STAT_LABELS:
        best_value = None
        best_score = None

        for candidate_label in _find_label_candidates(words, label):
            candidate = _nearest_number_above_label(candidate_label, number_words)
            if candidate is None:
                continue

            score = (candidate_label.top - candidate.bottom) * 10 + abs(candidate_label.center_x - candidate.center_x)
            if best_score is None or score < best_score:
                best_score = score
                best_value = candidate.value

        if best_value is not None:
            found[key] = best_value

    return found


def _find_stat_value(text: str, label: str) -> int | None:
    lowered = text.lower()
    for alias in (label, label.replace(" ", "")):
        alias_index = lowered.find(alias.lower())
        if alias_index == -1:
            continue

        before = text[max(0, alias_index - 24) : alias_index]
        after = text[alias_index + len(alias) : alias_index + len(alias) + 24]

        number = _nearest_number(before, reverse=True)
        if number is None:
            number = _nearest_number(after)
        if number is not None:
            return number
    return None


def _nearest_number(segment: str, reverse: bool = False) -> int | None:
    matches = list(NUMBER_PATTERN.finditer(segment))
    if not matches:
        return None
    match = matches[-1] if reverse else matches[0]
    return int(match.group(0).replace(",", ""))


def _looks_like_profile_text(text: str) -> bool:
    return bool(text) and any(char.isalpha() for char in text)


def _is_excluded_profile_phrase(text: str) -> bool:
    lowered = text.lower().strip()
    return lowered in EXCLUDES


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _looks_like_number_word(text: str) -> bool:
    return bool(NUMBER_PATTERN.fullmatch(text.replace(" ", "")))


def _find_label_candidates(words: list[OcrWord], label: str) -> list[OcrWord]:
    normalized_label = _normalize_text(label)
    candidates: list[OcrWord] = []
    for word in words:
        normalized_word = _normalize_text(word.text)
        if not normalized_word:
            continue
        if normalized_label in normalized_word or label.replace(" ", "") in normalized_word:
            candidates.append(word)
    return candidates


@dataclass(slots=True)
class _NumberCandidate:
    value: int
    center_x: float
    bottom: int


def _nearest_number_above_label(label: OcrWord, numbers: list[OcrWord]) -> _NumberCandidate | None:
    best: _NumberCandidate | None = None
    best_score: float | None = None

    for number in numbers:
        if number.bottom > label.top + 20:
            continue

        x_distance = abs(number.center_x - label.center_x)
        if x_distance > 220:
            continue

        vertical_gap = label.top - number.bottom
        score = vertical_gap * 8 + x_distance
        if best_score is None or score < best_score:
            best_score = score
            best = _NumberCandidate(
                value=int(number.text.replace(",", "")),
                center_x=number.center_x,
                bottom=number.bottom,
            )

    return best