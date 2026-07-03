from __future__ import annotations

import re

from .consts import DEFAULT_IMAGES_URL, EXCLUDES, NUMBER_PATTERN, STAT_LABELS
from .models import DeadlockProfile, DeadlockStats
from .ocr import OcrWord, ProfileOcr, group_words_into_lines, line_text


def parse_deadlock_stats(capture: ProfileOcr) -> DeadlockStats:
    found: dict[str, int] = {}

    for key, label in STAT_LABELS:
        value = _extract_region_number(capture.stats.get(key, []), label)
        if value is not None:
            found[key] = value

    missing = [name for name, _ in STAT_LABELS if name not in found]
    if missing:
        raise ValueError(f"Could not extract from OCR regions: {', '.join(missing)}")

    return DeadlockStats(
        games_played=found["games_played"],
        games_won=found["games_won"],
        commends=found["commends"],
        kills=found["kills"],
        assists=found["assists"],
        denies=found["denies"],
    )


def parse_deadlock_profile(capture: ProfileOcr, hero_image_base_url: str = DEFAULT_IMAGES_URL) -> DeadlockProfile:
    stats = parse_deadlock_stats(capture)
    nickname = extract_nickname(capture.nickname)
    top_hero = extract_top_hero(capture.top_hero)
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
    return _extract_profile_text(words, max_words=4)


def extract_top_hero(words: list[OcrWord]) -> str | None:
    return _extract_profile_text(words, max_words=3)


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


def _extract_region_number(words: list[OcrWord], label: str) -> int | None:
    lines = group_words_into_lines(words)
    normalized_label = _normalize_text(label)

    for line in lines:
        text = line_text(line).strip()
        if not text:
            continue
        if normalized_label in _normalize_text(text):
            number = _nearest_number(text)
            if number is not None:
                return number

    for line in lines:
        number = _nearest_number(line_text(line))
        if number is not None:
            return number

    return None


def _extract_profile_text(words: list[OcrWord], max_words: int) -> str | None:
    candidates: list[tuple[int, int, str]] = []

    for line in group_words_into_lines(words):
        text = line_text(line).strip()
        if not _looks_like_profile_text(text):
            continue
        if any(char.isdigit() for char in text):
            continue
        if _is_excluded_profile_phrase(text):
            continue

        word_count = len(text.split())
        if word_count > max_words:
            continue

        candidates.append((word_count, -len(text), text))

    if not candidates:
        return None

    return min(candidates)[2]


def _nearest_number(segment: str) -> int | None:
    match = NUMBER_PATTERN.search(segment)
    if match is None:
        return None
    return int(match.group(0).replace(",", ""))


def _looks_like_profile_text(text: str) -> bool:
    return bool(text) and any(char.isalpha() for char in text)


def _is_excluded_profile_phrase(text: str) -> bool:
    return text.lower().strip() in EXCLUDES


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())