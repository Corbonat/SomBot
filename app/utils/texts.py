from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

_TEXTS_DIR = Path(__file__).resolve().parent.parent / "texts"


@lru_cache
def load_texts(locale: str = "ru") -> Dict[str, Any]:
    path = _TEXTS_DIR / f"{locale}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Texts for locale {locale} not found at {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_text(key: str, locale: str = "ru") -> Any:
    texts = load_texts(locale)
    value: Any = texts
    for part in key.split('.'):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise KeyError(f"Text key {key} not found for locale {locale}")
    return value
