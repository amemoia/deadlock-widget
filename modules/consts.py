import os
from pathlib import Path
import re

ENV_FILE = Path(".env")

DL_APPID = 1422450

# feel free to change this to match your steam install directory
# this could also work as a list of paths to search,
# might be useful if u sometimes take screenshots with ShareX or similar
SCR_DIR = Path(os.environ.get("PROGRAMFILES(X86)")) / "Steam" / "userdata" / "*" / "760" / "remote" / str(DL_APPID) / "screenshots"

# passing a url thats too long could result in an error
DEFAULT_IMAGES_URL = "https://raw.githubusercontent.com/amemoia/deadlock-widget/main/renders"

FILETYPES = {".png", ".jpg", ".jpeg"}

ENV_REQUIRED = (
    "DISCORD_APPLICATION_ID",
    "DISCORD_USER_ID",
    "DISCORD_WIDGET_USERNAME",
    "DISCORD_BOT_TOKEN",
)
ENV_ORDER = (
    "DISCORD_APPLICATION_ID",
    "DISCORD_USER_ID",
    "DISCORD_WIDGET_USERNAME",
    "DISCORD_BOT_TOKEN",
    "DISCORD_IDENTITY_ID",
    "DISCORD_WIDGET_HERO_IMAGE_BASE_URL",
)

VALUE_PROMPTS = {
    "DISCORD_APPLICATION_ID": "Paste your widget's Discord Application ID",
    "DISCORD_USER_ID": "Paste the Discord user ID whose widget should be updated",
    "DISCORD_WIDGET_USERNAME": "Enter a username to be sent along the widget update, this is required but the actual value does not matter at all",
    "DISCORD_BOT_TOKEN": "Paste the bot token tied to your application ID",
    "DISCORD_IDENTITY_ID": "(Optional) Use only if you know what you're doing, defaults to 0",
    "DISCORD_WIDGET_HERO_IMAGE_BASE_URL": "(Optional) Use only if you want to change where you get images from",
    "MANUAL_NICKNAME": "Nickname",
    "MANUAL_TOP_HERO": "Most played hero",
    "MANUAL_GAMES_PLAYED": "Games played",
    "MANUAL_GAMES_WON": "Games won",
    "MANUAL_COMMENDS": "Commends received",
    "MANUAL_KILLS": "Total kills",
    "MANUAL_ASSISTS": "Total assists",
    "MANUAL_DENIES": "Deny count",
}

STAT_LABELS = (
    ("games_played", "games played"),
    ("games_won", "games won"),
    ("commends", "commends"),
    ("kills", "kills"),
    ("assists", "assists"),
    ("denies", "denies"),
)

NUMBER_PATTERN = re.compile(r"\b\d[\d,]*\b")

EXCLUDES = {
    "match history",
    "showcase",
    "sort by",
    "view all match history",
    "view global leaderboards",
    "all heroes",
    "view forum login info",
    "friend code",
}