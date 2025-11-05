from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class RateSource(str, Enum):
    BYBIT = "bybit"
    RAPIRA = "rapira"
    GRINEX = "grinex"


class RateMethod(str, Enum):
    MID = "mid"
    BEST = "best"
    VWAP = "vwap"
    MEDIAN = "median"
    TRIMMED_MEAN = "trimmed_mean"


class BybitMode(str, Enum):
    ORDERBOOK = "orderbook"
    P2P = "p2p"
    COMPOSED = "composed"


class GeoOption(str, Enum):
    NONE = "none"
    RIO = "rio"
    BERLIN = "berlin"


class RatePayload(BaseModel):
    source: RateSource
    method: RateMethod
    mode: BybitMode = BybitMode.ORDERBOOK
    geo: GeoOption = GeoOption.NONE
    depth: Optional[int] = None
    value: Decimal = Field(..., decimal_places=6)
    updated_at: datetime
    valid_until: Optional[datetime] = None
    stale: bool = False
    extras: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("value", mode="before")
    @classmethod
    def _quantize_value(cls, v: Any) -> Decimal:
        dv = v if isinstance(v, Decimal) else Decimal(str(v))
        return dv.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


class CachedRate(BaseModel):
    payload: RatePayload
    raw_source: Dict[str, Any] = Field(default_factory=dict)


class RateQuery(BaseModel):
    source: RateSource
    method: RateMethod
    geo: GeoOption = GeoOption.NONE
    mode: BybitMode = BybitMode.ORDERBOOK
    depth: Optional[int] = None
