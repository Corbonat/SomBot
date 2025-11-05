from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

import orjson


class AmlResult(Dict[str, Any]):
    """Result of AML check.

    Expected keys:
      - address: str
      - chain: str | None
      - valid: bool
      - risk_level: str (low|medium|high|unknown|invalid)
      - score: int | None (0..100)
      - indicators: list[str]
      - sources: list[str]
      - created_at: str (ISO8601)
      - details: dict[str, Any]
    """


class AmlProvider(Protocol):
    async def check_address(self, address: str) -> AmlResult:  # pragma: no cover - protocol
        ...


class BasicHeuristicsProvider:
    """Heuristic AML provider with lightweight validation and basic risk scoring.

    This provider does not call external services. It validates popular
    address formats (BTC/ETH/TRON) and assigns a naive risk score.
    """

    # Very small illustrative blocklist (add real ones via a DB or config later)
    KNOWN_HIGH_RISK: set[str] = set()
    KNOWN_MEDIUM_RISK: set[str] = set()

    _ETH_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
    _BTC_BASE58_RE = re.compile(r"^[123][1-9A-HJ-NP-Za-km-z]{25,34}$")
    _BTC_BECH32_RE = re.compile(r"^(bc1)[0-9ac-hj-np-z]{11,71}$")
    _TRX_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")

    async def check_address(self, address: str) -> AmlResult:
        trimmed = address.strip()
        chain = self._detect_chain(trimmed)
        valid = self._is_valid_for_chain(trimmed, chain) if chain is not None else False

        indicators: List[str] = []
        risk_level = "invalid" if not valid else "unknown"
        score: Optional[int] = None

        if valid:
            normalized = trimmed.lower()
            if normalized in (a.lower() for a in self.KNOWN_HIGH_RISK):
                risk_level = "high"
                score = 90
                indicators.append("listed_high_risk")
            elif normalized in (a.lower() for a in self.KNOWN_MEDIUM_RISK):
                risk_level = "medium"
                score = 60
                indicators.append("listed_medium_risk")
            else:
                # Default conservative baseline
                risk_level = "low"
                score = 10
                indicators.append("no_hits")
        else:
            indicators.append("invalid_format")

        return AmlResult(
            address=trimmed,
            chain=chain,
            valid=valid,
            risk_level=risk_level,
            score=score,
            indicators=indicators,
            sources=["heuristics"],
            created_at=datetime.now(timezone.utc).isoformat(),
            details={},
        )

    def _detect_chain(self, address: str) -> Optional[str]:
        if self._ETH_RE.match(address):
            return "ETH"
        if self._BTC_BASE58_RE.match(address) or self._BTC_BECH32_RE.match(address):
            return "BTC"
        if self._TRX_RE.match(address):
            return "TRON"
        return None

    def _is_valid_for_chain(self, address: str, chain: Optional[str]) -> bool:
        if chain == "ETH":
            return bool(self._ETH_RE.match(address))
        if chain == "BTC":
            return bool(self._BTC_BASE58_RE.match(address) or self._BTC_BECH32_RE.match(address))
        if chain == "TRON":
            return bool(self._TRX_RE.match(address))
        return False


class AMLService:
    def __init__(self, provider: Optional[AmlProvider] = None) -> None:
        self._provider: AmlProvider = provider or BasicHeuristicsProvider()

    async def check_address(self, address: str) -> AmlResult:
        return await self._provider.check_address(address)

    async def export_report(self, result: AmlResult, fmt: str = "json") -> bytes:
        if fmt.lower() == "json":
            # orjson returns bytes
            return orjson.dumps(result)  # type: ignore[arg-type]
        # Other formats not yet implemented
        return orjson.dumps({"error": "unsupported_format", "format": fmt})
