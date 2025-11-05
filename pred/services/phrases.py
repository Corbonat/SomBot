from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

_DEFAULT_PHRASES = [
    "Люди в черном уже выехали за тобой — жди гостей",
    "Сбербанк особенно добр к тебе в этом месяце. Работай",
    "Еще чуть-чуть и трафик польется рекой, вот увидишь",
    "Mercurio благословили тебя и занесли в список везунчиков",
]


@dataclass
class Phrase:
    text: str
    tag: Optional[str] = None


class PhraseService:
    def __init__(self) -> None:
        self._phrases: List[Phrase] = [Phrase(text=t) for t in _DEFAULT_PHRASES]

    async def get_random_phrase(self, tag: Optional[str] = None) -> Phrase:
        # TODO: pull phrases from database with filters and stop-words checks.
        filtered = [p for p in self._phrases if tag is None or p.tag == tag]
        phrase = random.choice(filtered or self._phrases)
        return Phrase(text=f"{phrase.text} #нефинсовет", tag=phrase.tag)
