from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class DeadlockStats:
    games_played: int
    games_won: int
    commends: int
    kills: int
    assists: int
    denies: int
    
    def as_dict(self) -> dict[str, int]:
        return {
            "games_played": self.games_played,
            "games_won": self.games_won,
            "commends": self.commends,
            "kills": self.kills,
            "assists": self.assists,
            "denies": self.denies,
        }


@dataclass(slots=True)
class DeadlockProfile:
    username: str
    stats: DeadlockStats
    nickname: str | None
    top_hero: str | None
    hero_image_url: str | None
    hero_card_url: str | None