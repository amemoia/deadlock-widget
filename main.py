from __future__ import annotations

import builtins
import shutil
import subprocess
import sys
import os
from dataclasses import replace
from importlib.util import find_spec
from pathlib import Path


def _bootstrap_requirements() -> None:
    requirements = Path(__file__).with_name("requirements.txt")
    missing = [name for name in ("dotenv", "PIL") if find_spec(name) is None]
    if find_spec("pytesseract") is None and find_spec("rapidocr_onnxruntime") is None:
        missing.append("pytesseract|rapidocr_onnxruntime")

    if not missing:
        return

    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements)])

_bootstrap_requirements()

from dotenv import load_dotenv, set_key

from modules.models import DeadlockProfile, DeadlockStats
from modules.ocr import get_ocr_backend_name, get_tesseract_exe, group_words_into_lines, line_text, run_ocr, save_region_debug_crops, save_region_debug_image
from modules.parser import build_hero_card_url, build_hero_image_url, parse_deadlock_profile
from modules.screenshot import find_latest_scr
from modules.widget_client import DiscordWidgetClient

from modules.consts import ENV_FILE, ENV_ORDER, ENV_REQUIRED, VALUE_PROMPTS, DEFAULT_IMAGES_URL

def env_handle_missing(values: dict[str, str]) -> dict[str, str]:
    for key in ENV_REQUIRED:
        if values.get(key):
            continue
        entered = input(f"{VALUE_PROMPTS[key]}:\n").strip()
        if not entered:
            raise SystemExit(f"Missing required value for {key}")
        values[key] = entered

    values.setdefault("DISCORD_IDENTITY_ID", "0")
    values.setdefault("DISCORD_WIDGET_HERO_IMAGE_BASE_URL", DEFAULT_IMAGES_URL)
    return values


def env_write(values: dict[str, str], path: Path = ENV_FILE) -> None:
    for key in ENV_ORDER:
        value = values.get(key)
        if value: set_key(str(path), key, value, quote_mode="never")


def resolve_tesseract(values: dict[str, str]) -> dict[str, str]:
    if shutil.which("tesseract") is not None:
        return values

    tesseract_exe = get_tesseract_exe()
    if tesseract_exe is not None and tesseract_exe.exists():
        return values

    entered = builtins.input(f"{VALUE_PROMPTS['TESSERACT_DIR']}:\n").strip()
    if not entered:
        raise SystemExit("Missing Tesseract directory or RapidOCR selection")

    if entered.lower() in {"no", "n"}:
        values["TESSERACT_DIR"] = "no"
        os.environ["TESSERACT_DIR"] = "no"
        env_write(values)
        return values

    candidate = Path(entered.strip('"'))
    candidate_exe = candidate / "tesseract.exe"
    if not candidate_exe.exists():
        print(f"Could not find tesseract.exe in: {candidate}")
        return resolve_tesseract(values)

    values["TESSERACT_DIR"] = str(candidate)
    os.environ["TESSERACT_DIR"] = str(candidate)
    env_write(values)
    return values


def prompt_int(prompt: str) -> int:
    while True:
        try: return int(builtins.input(f"{prompt}:\n").strip().replace(",", ""))
        except ValueError: print("Not an int")


def manual_profile(hero_image_base_url: str, build_hero_image_url, build_hero_card_url):
    nickname = builtins.input(f"{VALUE_PROMPTS['MANUAL_NICKNAME']}:\n").strip()
    top_hero = builtins.input(f"{VALUE_PROMPTS['MANUAL_TOP_HERO']}:\n").strip()

    stats = DeadlockStats(
        games_played=prompt_int(VALUE_PROMPTS["MANUAL_GAMES_PLAYED"]),
        games_won=prompt_int(VALUE_PROMPTS["MANUAL_GAMES_WON"]),
        commends=prompt_int(VALUE_PROMPTS["MANUAL_COMMENDS"]),
        kills=prompt_int(VALUE_PROMPTS["MANUAL_KILLS"]),
        assists=prompt_int(VALUE_PROMPTS["MANUAL_ASSISTS"]),
        denies=prompt_int(VALUE_PROMPTS["MANUAL_DENIES"]),
    )

    profile = DeadlockProfile(
        username=nickname,
        stats=stats,
        nickname=nickname,
        top_hero=top_hero,
        hero_image_url=None,
        hero_card_url=None,
    )

    return replace(
        profile,
        hero_image_url=build_hero_image_url(top_hero, hero_image_base_url),
        hero_card_url=build_hero_card_url(top_hero, hero_image_base_url),
    )


def valuecheck(profile, values: dict[str, str]) -> None:
    missing = [key for key in ENV_REQUIRED if not values.get(key)]
    missing.extend(
        name
        for name, value in {
            "username": profile.username,
            "nickname": profile.nickname,
            "top_hero": profile.top_hero,
            "hero_image_url": profile.hero_image_url,
            "hero_card_url": profile.hero_card_url,
        }.items()
        if not value
    )

    if missing:
        print("Not updating the widget because these values are empty or missing:")
        for item in missing:
            print(f"- {item}")
        raise SystemExit(1)


def lencheck(profile) -> None:
    over_limit = [
        (field_name, value)
        for field_name, value in (
            ("hero_image_url", profile.hero_image_url),
            ("hero_card_url", profile.hero_card_url),
            ("nickname", profile.nickname),
            ("top_hero", profile.top_hero),
            ("username", profile.username),
        )
        if value is not None and len(value) > 100
    ]

    if over_limit:
        print("Not updating the widget because these values go over discord's 100 character limit:")
        for field_name, value in over_limit:
            print(f"- {field_name}: {len(value)} characters")
        print("To fix this, you might need to host the images used by the widget somewhere else")
        raise SystemExit(1)


def show_result(profile, screenshot: Path | None) -> None:
    if screenshot is not None:
        print(f"Using screenshot: {screenshot}")
    else:
        print("Using manual input mode")

    print(f"username: {profile.username}")
    print(f"nickname: {profile.nickname or ''}")
    print(f"top_hero: {profile.top_hero or ''}")
    print(f"hero_image_url: {profile.hero_image_url or ''}")
    print(f"hero_card_url: {profile.hero_card_url or ''}")
    for name, value in profile.stats.as_dict().items():
        print(f"{name}: {value}")


def main() -> int:
    load_dotenv(ENV_FILE)
    values = {key: value for key, value in os.environ.items() if key.startswith("DISCORD_")}
    values = env_handle_missing(values)
    values = resolve_tesseract(values)
    env_write(values)
    debug_regions = values.get("DISCORD_WIDGET_DEBUG_REGIONS", "").strip().lower() in {"1", "true", "yes", "y"}

    if values.get("DISCORD_WIDGET_MANUAL_MODE", "").strip().lower() in {"1", "true", "yes", "y"}:
        profile = manual_profile(values["DISCORD_WIDGET_HERO_IMAGE_BASE_URL"], build_hero_image_url, build_hero_card_url)
        screenshot = None
    else:
        screenshot = find_latest_scr()
        print(f"Choosing screenshot: {screenshot}")
        if debug_regions:
            debug_image = save_region_debug_image(screenshot)
            print(f"Saved OCR region debug image: {debug_image}")
            debug_dir = save_region_debug_crops(screenshot)
            print(f"Saved OCR region crops: {debug_dir}")
        print(f"Running OCR using {get_ocr_backend_name()}! This might take a minute...")
        capture = run_ocr(screenshot)
        try:
            profile = parse_deadlock_profile(capture, hero_image_base_url=values["DISCORD_WIDGET_HERO_IMAGE_BASE_URL"])
        except ValueError as exc:
            print(f"Selected file: {screenshot}")
            print(f"Exception during OCR: {exc}")
            print("OCR detected regions:")
            for region_name, region_words in _iter_ocr_regions(capture):
                print(f"[{region_name}]")
                for line in group_words_into_lines(region_words):
                    print(line_text(line))
            raise
        profile.username = values["DISCORD_WIDGET_USERNAME"]

    show_result(profile, screenshot)
    valuecheck(profile, values)
    lencheck(profile)

    DiscordWidgetClient(
        application_id=values["DISCORD_APPLICATION_ID"],
        discord_user_id=values["DISCORD_USER_ID"],
        identity_id=values.get("DISCORD_IDENTITY_ID", "0"),
        token=values["DISCORD_BOT_TOKEN"],
    ).update(profile)
    return 0


def _iter_ocr_regions(capture):
    yield "nickname", capture.nickname
    yield "top_hero", capture.top_hero
    for key in ("games_played", "games_won", "commends", "kills", "assists", "denies"):
        yield key, capture.stats.get(key, [])


if __name__ == "__main__":
    raise SystemExit(main())
