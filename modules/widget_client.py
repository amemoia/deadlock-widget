from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
from urllib import error, request
from .models import DeadlockProfile, DeadlockStats

@dataclass(slots=True)
class DiscordWidgetClient:
    application_id: str
    discord_user_id: str
    identity_id: str = "0"
    token: str | None = None
    timeout: float = 15.0

    def build_request_url(self) -> str:
        return (
            "https://discord.com/api/v9/applications/"
            f"{quote(self.application_id, safe='')}/users/{quote(self.discord_user_id, safe='')}/"
            f"identities/{quote(self.identity_id, safe='')}/profile"
        )

    def build_payload(self, profile: DeadlockProfile) -> dict[str, Any]:
        dynamic: list[dict[str, Any]] = []

        # type 1 is for string values
        if profile.nickname is not None: dynamic.append({"type": 1, "name": "nickname", "value": profile.nickname})
        if profile.top_hero is not None: dynamic.append({"type": 1, "name": "top_hero", "value": profile.top_hero})

        # type 2 is for number values
        dynamic.extend(
            [
                { "type": 2,  "name": "games_played",  "value": profile.stats.games_played },
                { "type": 2,  "name": "games_won",     "value": profile.stats.games_won    },
                { "type": 2,  "name": "commends",      "value": profile.stats.commends     },
                { "type": 2,  "name": "kills",         "value": profile.stats.kills        },
                { "type": 2,  "name": "assists",       "value": profile.stats.assists      },
                { "type": 2,  "name": "denies",        "value": profile.stats.denies       },
            ]
        )

        # to pass an image, we need to use type 3 which is for objects, and send a { "url" : URL_TO_IMAGE } object
        if profile.hero_image_url is not None: dynamic.append({"type": 3, "name": "hero_image_url", "value": {"url": profile.hero_image_url}})
        if profile.hero_card_url is not None:  dynamic.append({"type": 3, "name": "hero_card_url", "value": {"url": profile.hero_card_url}})

        return {
            "username": profile.username,
            "data": {"dynamic": dynamic},
        }
    
    def build_payload_json(self, profile: DeadlockProfile) -> str: return json.dumps(self.build_payload(profile), indent=2)

    def update(self, profile: DeadlockProfile) -> None:
        req = self.build_request(profile)
        print(self.build_payload_json(profile))
        try:
            with request.urlopen(req, timeout=self.timeout) as response: response.read()
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Couldnt update widget, HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Couldnt update widget: {exc.reason}") from exc

    def build_request(self, profile: DeadlockProfile) -> request.Request:
        payload = self.build_payload_json(profile).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DiscordBot (https://github.com/discord/discord-api-docs, 1.0.0)",
        }
        if self.token:
            headers["Authorization"] = f"Bot {self.token}"

        return request.Request(self.build_request_url(), data=payload, headers=headers, method="PATCH")

