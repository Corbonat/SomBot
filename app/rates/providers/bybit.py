from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Tuple

import httpx

from app.rates.models import BybitMode, CachedRate, GeoOption, RateMethod, RatePayload, RateQuery, RateSource
from app.rates.providers.base import BaseRateProvider


class BybitProvider(BaseRateProvider):
    source = RateSource.BYBIT

    def __init__(self, client: httpx.AsyncClient, endpoint: str) -> None:
        super().__init__(client)
        # If not provided via env, default to a public, no-key endpoint (USD->RUB)
        # We treat USDT≈USD for fiat conversion when Bybit spot pair is unavailable
        self.endpoint = (
            endpoint or "https://api.exchangerate.host/latest?base=USD&symbols=RUB"
        )

    @staticmethod
    def _compute_mid_from_orderbook(bids: List[Tuple[str, str]], asks: List[Tuple[str, str]]) -> Decimal:
        if not bids or not asks:
            raise ValueError("Orderbook is empty")
        best_bid = Decimal(str(bids[0][0]))
        best_ask = Decimal(str(asks[0][0]))
        return (best_bid + best_ask) / Decimal("2")

    @staticmethod
    def _compute_vwap(levels: List[Tuple[str, str]], depth: int) -> Decimal:
        # levels: list of [price, qty]
        taken = levels[: max(depth, 1)]
        total_notional = Decimal("0")
        total_qty = Decimal("0")
        for price, qty in taken:
            p = Decimal(str(price))
            q = Decimal(str(qty))
            total_notional += p * q
            total_qty += q
        if total_qty == 0:
            raise ValueError("VWAP computation has zero quantity")
        return total_notional / total_qty

    @staticmethod
    def _extract_price_from_bybit_v5(data: Dict[str, Any], method: str, depth: int) -> Decimal:
        # Accepts response for /v5/market/orderbook or /v5/market/tickers
        result = data.get("result") or {}
        if "b" in result and "a" in result:  # orderbook format
            bids = result.get("b", [])
            asks = result.get("a", [])
            if method == "vwap":
                bid_vwap = BybitProvider._compute_vwap(bids, depth)
                ask_vwap = BybitProvider._compute_vwap(asks, depth)
                return (bid_vwap + ask_vwap) / Decimal("2")
            if method == "best":
                return BybitProvider._compute_mid_from_orderbook(bids, asks)
            return BybitProvider._compute_mid_from_orderbook(bids, asks)
        tickers = result.get("list") or []
        if tickers:
            item = tickers[0]
            # Prefer mid of bid1 and ask1 if present, else use lastPrice
            bid = item.get("bid1Price") or item.get("bidPrice")
            ask = item.get("ask1Price") or item.get("askPrice")
            last = item.get("lastPrice")
            try:
                if bid and ask:
                    return (Decimal(str(bid)) + Decimal(str(ask))) / Decimal("2")
                if last:
                    return Decimal(str(last))
            except InvalidOperation as exc:
                raise ValueError("Invalid numeric value in ticker") from exc
        raise ValueError("Unsupported Bybit response shape")

    @staticmethod
    def _extract_price_from_exchangerate_host(data: Dict[str, Any]) -> Decimal:
        rates = data.get("rates") or {}
        rub = rates.get("RUB")
        if rub is None:
            raise ValueError("RUB rate not found in response")
        return Decimal(str(rub))

    @staticmethod
    def _extract_bid_ask_from_bybit_v5(data: Dict[str, Any]) -> Tuple[Decimal, Decimal]:
        """Извлекает bid и ask цены из ответа Bybit v5 API."""
        result = data.get("result") or {}
        if "b" in result and "a" in result:  # orderbook format
            bids = result.get("b", [])
            asks = result.get("a", [])
            if not bids or not asks:
                raise ValueError("Orderbook is empty")
            best_bid = Decimal(str(bids[0][0]))
            best_ask = Decimal(str(asks[0][0]))
            return best_bid, best_ask
        tickers = result.get("list") or []
        if tickers:
            item = tickers[0]
            bid = item.get("bid1Price") or item.get("bidPrice")
            ask = item.get("ask1Price") or item.get("askPrice")
            if bid and ask:
                return Decimal(str(bid)), Decimal(str(ask))
        raise ValueError("Unsupported Bybit response shape for bid/ask")

    async def fetch_bid_ask(self, query: RateQuery) -> Tuple[Decimal, Decimal]:
        """Получает bid и ask цены для Bybit."""
        url = self.endpoint
        
        async def _get_json(target: str) -> Dict[str, Any]:
            resp = await self.client.get(target)
            resp.raise_for_status()
            return resp.json()

        try:
            if "api.bybit.com" in url:
                try:
                    ob = await _get_json(
                        f"{url.rstrip('/')}/v5/market/orderbook?category=spot&symbol=USDTRUB&limit=1"
                    )
                    return self._extract_bid_ask_from_bybit_v5(ob)
                except Exception:
                    tickers = await _get_json(
                        f"{url.rstrip('/')}/v5/market/tickers?category=spot&symbol=USDTRUB"
                    )
                    return self._extract_bid_ask_from_bybit_v5(tickers)
            else:
                data = await _get_json(url)
                if "orderbook" in data and isinstance(data["orderbook"], dict):
                    ob = data["orderbook"]
                    bids = ob.get("bids") or []
                    asks = ob.get("asks") or []
                    if not bids or not asks:
                        raise ValueError("Orderbook is empty")
                    best_bid = Decimal(str(bids[0][0]))
                    best_ask = Decimal(str(asks[0][0]))
                    return best_bid, best_ask
                raise ValueError("Unsupported response format for endpoint")
        except Exception:
            # Fallback: используем среднюю цену как bid и ask
            fx_rate, _ = await self.fetch_usd_to_rub_no_key()
            # Используем небольшой спред для bid/ask
            spread = fx_rate * Decimal("0.01")  # 1% спред
            return fx_rate - spread, fx_rate + spread

    async def fetch(self, query: RateQuery) -> CachedRate:
        # Strategy:
        # 1) Try Bybit public endpoints if endpoint looks like api.bybit.com and mode=orderbook
        # 2) Otherwise, treat endpoint as a full URL returning JSON and try to extract a value
        # 3) As a safe default, exchangerate.host latest USD->RUB w/o API keys

        mode = query.mode if isinstance(query.mode, BybitMode) else BybitMode(query.mode)
        geo = query.geo if isinstance(query.geo, GeoOption) else GeoOption(query.geo)
        method_str = query.method.value if hasattr(query.method, "value") else str(query.method)
        depth = query.depth or 5

        url = self.endpoint
        value: Decimal
        raw: Dict[str, Any] = {}

        async def _get_json(target: str) -> Dict[str, Any]:
            resp = await self.client.get(target)
            resp.raise_for_status()
            return resp.json()

        try:
            if "api.bybit.com" in url:
                # Prefer deriving USDT/USD ratio from Bybit tickers (derivatives if needed)
                # USDT/USD = Price(BTCUSDT) / Price(BTCUSD) inverted? We want USD per USDT = BTCUSD / BTCUSDT
                # Final USDT->RUB = (BTCUSD_last / BTCUSDT_last) * (USD->RUB)
                try:
                    lin = await _get_json(
                        f"{url.rstrip('/')}/v5/market/tickers?category=linear&symbol=BTCUSDT"
                    )
                    inv = await _get_json(
                        f"{url.rstrip('/')}/v5/market/tickers?category=inverse&symbol=BTCUSD"
                    )
                    raw = {"linear": lin, "inverse": inv}
                    def _last(d: Dict[str, Any]) -> Decimal:
                        lst = (d.get("result") or {}).get("list") or []
                        if not lst:
                            raise ValueError("Empty ticker list")
                        return Decimal(str(lst[0].get("lastPrice")))
                    btcusdt = _last(lin)
                    btcusd = _last(inv)
                    usd_per_usdt = btcusd / btcusdt
                    fx, fx_raw = await self.fetch_usd_to_rub_no_key()
                    value = usd_per_usdt * fx
                    raw["fx"] = fx_raw
                except Exception:
                    # If ratio path fails, try spot USDTRUB (rarely available)
                    if mode == BybitMode.ORDERBOOK:
                        try:
                            ob = await _get_json(
                                f"{url.rstrip('/')}/v5/market/orderbook?category=spot&symbol=USDTRUB&limit={max(depth,1)}"
                            )
                            raw = ob
                            value = self._extract_price_from_bybit_v5(ob, method_str, depth)
                        except Exception:
                            tickers = await _get_json(
                                f"{url.rstrip('/')}/v5/market/tickers?category=spot&symbol=USDTRUB"
                            )
                            raw = tickers
                            value = self._extract_price_from_bybit_v5(tickers, method_str, depth)
                    else:
                        # Non-orderbook modes: fall back directly
                        value, raw = await self.fetch_usd_to_rub_no_key()
            else:
                data = await _get_json(url)
                raw = data
                if "rates" in data:
                    value = self._extract_price_from_exchangerate_host(data)
                else:
                    # Try common shapes
                    if isinstance(data.get("price"), (int, float, str)):
                        value = Decimal(str(data["price"]))
                    elif "orderbook" in data and isinstance(data["orderbook"], dict):
                        ob = data["orderbook"]
                        bids = ob.get("bids") or []
                        asks = ob.get("asks") or []
                        if method_str == "vwap":
                            bid_vwap = self._compute_vwap(bids, depth)
                            ask_vwap = self._compute_vwap(asks, depth)
                            value = (bid_vwap + ask_vwap) / Decimal("2")
                        else:
                            value = self._compute_mid_from_orderbook(bids, asks)
                    else:
                        raise ValueError("Unsupported response format for endpoint")
        except Exception:
            # Fallback to public fiat rate (USDT≈USD)
            value, raw = await self.fetch_usd_to_rub_no_key()

        payload = RatePayload(
            source=self.source,
            method=query.method,
            mode=mode,
            geo=geo,
            depth=query.depth,
            value=value,
            updated_at=datetime.now(timezone.utc),
            extras={"endpoint": url, "note": "public-no-key"},
        )
        return CachedRate(payload=payload, raw_source=raw)
