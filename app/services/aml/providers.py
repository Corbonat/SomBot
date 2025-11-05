from __future__ import annotations

from typing import Any, Dict, Optional, List, Tuple

import asyncio
import re
import httpx

from app.services.aml.service import AmlResult, AmlProvider


class GetBlockProvider(AmlProvider):
    """Provider that queries GetBlock JSON-RPC endpoints.

    Currently supports ETH-like chains via a single base URL with x-api-key header.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        chain: str = "ETH",
        blockchain: str = "eth",
        network: str = "mainnet",
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._chain = chain.upper()
        self._blockchain = blockchain
        self._network = network

    async def _rpc(self, method: str, params: Optional[list[Any]] = None) -> Any:
        # GetBlock v1 request schema requires blockchain/network in body
        payload: Dict[str, Any] = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "blockchain": self._blockchain,
            "network": self._network,
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
        }
        resp = await self._client.post(self._base_url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"GetBlock error: {data['error']}")
        return data.get("result")

    async def check_address(self, address: str) -> AmlResult:
        # Basic ETH checks: balance, tx count, code presence
        addr = address.strip()
        balance_hex = await self._rpc("eth_getBalance", [addr, "latest"])
        txcount_hex = await self._rpc("eth_getTransactionCount", [addr, "latest"])
        code_hex = await self._rpc("eth_getCode", [addr, "latest"])

        def hex_to_int(x: str) -> int:
            try:
                return int(x, 16)
            except Exception:
                return 0

        balance_wei = hex_to_int(balance_hex or "0x0")
        txcount = hex_to_int(txcount_hex or "0x0")
        is_contract = isinstance(code_hex, str) and code_hex not in ("0x", "0x0")

        indicators: list[str] = []
        if balance_wei > 0:
            indicators.append("has_balance")
        if txcount > 0:
            indicators.append("has_activity")
        if is_contract:
            indicators.append("is_contract")

        # Naive scoring: more activity => higher risk for demonstration
        score = min(100, (10 if balance_wei > 0 else 0) + (txcount * 2) + (20 if is_contract else 0))
        risk_level = "low"
        if score >= 70:
            risk_level = "high"
        elif score >= 40:
            risk_level = "medium"

        return AmlResult(
            address=addr,
            chain=self._chain,
            valid=True,
            risk_level=risk_level,
            score=score,
            indicators=indicators or ["no_hits"],
            sources=["getblock"],
            details={
                "balance_wei": balance_wei,
                "txcount": txcount,
                "is_contract": is_contract,
            },
        )


class GetBlockAmlProvider(AmlProvider):
    """Provider using GetBlock checkup.* AML methods with autodetection & polling."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        bearer_token: str,
        evm_probe_order: Optional[List[str]] = None,
        default_evm_chain: str = "ETH",
        timeout_sec: float = 8.0,
        poll_attempts: int = 10,
        poll_delay_ms: int = 1500,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._bearer = bearer_token
        self._evm_probe_order = [c.upper() for c in (evm_probe_order or ["ETH", "BSC", "MATIC", "ETC"])]
        self._default_evm_chain = default_evm_chain.upper()
        self._timeout = timeout_sec
        self._poll_attempts = poll_attempts
        self._poll_delay_ms = poll_delay_ms

    async def _rpc(self, method: str, params: Optional[dict] = None) -> Any:
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": "aml",
            "method": method,
            "params": params or {},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._bearer}",
        }
        resp = await self._client.post(self._base_url, headers=headers, json=payload, timeout=self._timeout)
        # Try to parse JSON error body without raising immediately
        data: Dict[str, Any]
        try:
            data = resp.json()
        except Exception:
            resp.raise_for_status()
            raise RuntimeError(f"Non-JSON response: HTTP {resp.status_code}")
        if data.get("error"):
            err = data["error"]
            code = err.get("code") if isinstance(err, dict) else None
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise RuntimeError(f"GetBlock AML error {code}: {msg}")
        return data.get("result")

    @staticmethod
    def _is_evm(addr: str) -> bool:
        return bool(re.match(r"^0x[a-fA-F0-9]{40}$", addr))

    @staticmethod
    def _quick_guess(addr: str) -> str:
        a = addr.strip()
        if re.match(r"^bc1[0-9ac-hj-np-z]{11,71}$", a, re.I):
            return "BTC"
        if re.match(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$", a):
            return "BTC"
        if re.match(r"^(bitcoincash:)?(q|p)[a-z0-9]{41}$", a, re.I):
            return "BCH"
        if re.match(r"^(ltc1[0-9ac-hj-np-z]{11,71}|[LM3][a-km-zA-HJ-NP-Z1-9]{26,33})$", a):
            return "LTC"
        if re.match(r"^T[1-9A-HJ-NP-Za-km-z]{33}$", a):
            return "TRX"
        if re.match(r"^r[1-9A-HJ-NP-Za-km-z]{24,34}$", a):
            return "XRP"
        if re.match(r"^G[ABCDEFGHIJKLMNOPQRSTUVWXYZ234567]{55}$", a):
            return "XLM"
        if re.match(r"^0x[a-fA-F0-9]{40}$", a):
            return "ETH"
        return "ETH"

    async def _findreport_has_checks(self, currency: str, value: str) -> bool:
        try:
            res = await self._rpc("checkup.findreport", {"hash": value, "currency": currency})
            checks = res.get("checks") if isinstance(res, dict) else None
            return bool(checks)
        except Exception as _:
            return False

    async def _resolve_currency(self, address: str, user_asset: Optional[str]) -> str:
        if user_asset:
            return user_asset.upper()
        guess = self._quick_guess(address)
        if guess != "ETH" or not self._is_evm(address):
            return guess
        for c in self._evm_probe_order:
            if await self._findreport_has_checks(c, address):
                return c
        return self._default_evm_chain

    @staticmethod
    def _normalize_score(raw: float) -> float:
        return raw * 100.0 if raw <= 1.0 else raw

    @staticmethod
    def _classify(score_100: float) -> str:
        if score_100 < 31.0:
            return "low"
        if score_100 < 70.0:
            return "medium"
        return "high"

    # --- Signals grouping ---
    _GROUPS: Dict[str, set[str]] = {
        "trusted": {
            "exchange_licensed",
            "miner",
            "wallet",
            "payment",
            "marketplace",
            "p2p_exchange_licensed",
            "other",
            # legacy
            "exchange_mlrisk_low",
        },
        "suspicious": {
            "liquidity_pools",
            "p2p_exchange_unlicensed",
            "exchange_unlicensed",
            # legacy
            "exchange_mlrisk_moderate",
        },
        "dangerous": {
            "sanctions",
            "scam",
            "stolen_coins",
            "mixer",
            "ransom",
            "child_exploitation",
            "dark_market",
            "dark_service",
            "illegal_service",
            "terrorism_financing",
            "seized_assets",
            "enforcement_action",
            "gambling",
            "atm",
            # legacy
            "exchange_mlrisk_high",
            "exchange_mlrisk_veryhigh",
        },
    }

    @classmethod
    def _group_signals(cls, signals: Dict[str, float]) -> Dict[str, Any]:
        buckets: Dict[str, List[Tuple[str, float]]] = {
            "trusted": [],
            "suspicious": [],
            "dangerous": [],
        }
        other: List[Tuple[str, float]] = []
        for key, value in (signals or {}).items():
            placed = False
            for group, keys in cls._GROUPS.items():
                if key in keys:
                    buckets[group].append((key, float(value)))
                    placed = True
                    break
            if not placed and value:
                other.append((key, float(value)))

        def summarize(items: List[Tuple[str, float]]) -> Tuple[float, str]:
            total = sum(v for _, v in items)
            top = sorted(items, key=lambda x: x[1], reverse=True)[:4]
            def as_pct(x: float) -> float:
                return round(x * 100.0 if x <= 1.0 else x, 2)
            top_str = ", ".join(f"{k} {as_pct(v)}%" for k, v in top) if top else "—"
            return as_pct(total), top_str

        t_pct, t_top = summarize(buckets["trusted"]) 
        s_pct, s_top = summarize(buckets["suspicious"]) 
        d_pct, d_top = summarize(buckets["dangerous"]) 
        return {
            "trusted_pct": t_pct,
            "trusted_top": t_top,
            "suspicious_pct": s_pct,
            "suspicious_top": s_top,
            "dangerous_pct": d_pct,
            "dangerous_top": d_top,
            "other": other,
        }

    async def _findreport_enrich(self, currency: str, addr_or_tx: str, check_hash: str) -> Dict[str, Any]:
        try:
            res = await self._rpc("checkup.findreport", {"hash": addr_or_tx, "currency": currency})
        except Exception:
            return {}
        checks = (res or {}).get("checks") or []
        if not checks:
            return {}
        by_hash = [c for c in checks if c.get("hash") == check_hash]
        chosen = by_hash[0] if by_hash else next((c for c in checks if c.get("status") == "SUCCESS"), checks[0])
        return {
            "pdfLink": chosen.get("pdfLink"),
            "shareLink": chosen.get("shareLink"),
            "counterparty": chosen.get("counterparty"),
        }

    async def check_address(self, address: str) -> AmlResult:  # type: ignore[override]
        addr = address.strip()
        currency = await self._resolve_currency(addr, None)
        submit = await self._rpc("checkup.checkaddr", {"addr": addr, "currency": currency})
        check = submit.get("check", {}) if isinstance(submit, dict) else {}
        check_hash = check.get("hash")
        if not check_hash:
            raise RuntimeError("No check hash returned")

        for _ in range(self._poll_attempts):
            res = await self._rpc("checkup.getresult", {"hash": check_hash})
            chk = res.get("check", {}) if isinstance(res, dict) else {}
            status = chk.get("status") or ""
            if status == "SUCCESS":
                report = chk.get("report") or {}
                raw = float(report.get("riskscore", 0.0))
                score_100 = self._normalize_score(raw)
                level = self._classify(score_100)
                grouped = self._group_signals(report.get("signals") or {})
                enrich = await self._findreport_enrich(currency, addr, check_hash)
                return AmlResult(
                    address=addr,
                    chain=currency,
                    valid=True,
                    risk_level=level,
                    score=round(score_100, 2),
                    indicators=["gb_checkup"],
                    sources=["getblock-aml"],
                    details={
                        "hash": check_hash,
                        "status": status,
                        "signals": report.get("signals"),
                        "risky_volume": report.get("risky_volume"),
                        "risky_volume_fiat": report.get("risky_volume_fiat"),
                    },
                    initDate=chk.get("initDate"),
                    resultDate=chk.get("resultDate"),
                    signals_grouped=grouped,
                    pdfLink=enrich.get("pdfLink"),
                    shareLink=enrich.get("shareLink"),
                    counterparty=enrich.get("counterparty"),
                )
            if status == "FAILED":
                raise RuntimeError("AML check FAILED")
            await asyncio.sleep(self._poll_delay_ms / 1000.0)

        raise RuntimeError("AML check TIMEOUT — no SUCCESS within attempts")

