from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

import httpx

from app.config import settings

log = logging.getLogger(__name__)


def _to_float(v: object) -> float | None:
    if v is None:
        return None
    if isinstance(v, (float, int)):
        return float(v)
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


class KalshiClient:
    def __init__(self) -> None:
        self.base = settings.kalshi_base_url.rstrip("/")

    async def fetch_markets_page(self, client: httpx.AsyncClient, cursor: str | None = None) -> dict:
        params: dict[str, str | int] = {"limit": 200, "status": "open"}
        if cursor:
            params["cursor"] = cursor
        r = await client.get(f"{self.base}/markets", params=params, timeout=30.0)
        r.raise_for_status()
        return r.json()

    async def fetch_orderbook(self, client: httpx.AsyncClient, ticker: str) -> dict:
        r = await client.get(f"{self.base}/markets/{ticker}/orderbook", timeout=30.0)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _best_yes_from_orderbook(ob: dict) -> tuple[float | None, float | None]:
        """Derive yes bid and synthetic yes ask from Kalshi reciprocal book."""
        ob_fp = ob.get("orderbook_fp") or ob.get("orderbook") or {}
        yes = ob_fp.get("yes_dollars") or []
        no = ob_fp.get("no_dollars") or []
        best_yes_bid: float | None = None
        if yes:
            try:
                best_yes_bid = float(yes[0][0])
            except (IndexError, TypeError, ValueError):
                best_yes_bid = None
        best_no_bid: float | None = None
        if no:
            try:
                best_no_bid = float(no[0][0])
            except (IndexError, TypeError, ValueError):
                best_no_bid = None
        yes_ask: float | None = None
        if best_no_bid is not None:
            yes_ask = max(0.0, min(1.0, 1.0 - best_no_bid))
        return best_yes_bid, yes_ask

    @staticmethod
    def _from_market_row(m: dict) -> tuple[float | None, float | None, float | None]:
        yb = _to_float(m.get("yes_bid_dollars")) or _to_float(m.get("yes_bid"))  # type: ignore[arg-type]
        ya = _to_float(m.get("yes_ask_dollars")) or _to_float(m.get("yes_ask"))
        vol = _to_float(m.get("volume_fp")) or _to_float(m.get("volume"))
        return yb, ya, vol

    async def sync_markets_snapshot(self) -> list[dict]:
        """Pull open markets (paginated) and enrich top-N with orderbooks."""
        out: list[dict] = []
        cursor: str | None = None
        async with httpx.AsyncClient() as client:
            for _ in range(25):
                data = await self.fetch_markets_page(client, cursor)
                markets = data.get("markets") or []
                for m in markets:
                    ticker = m.get("ticker")
                    if not ticker:
                        continue
                    yb, ya, vol = self._from_market_row(m)
                    close_time = m.get("expected_expiration_time") or m.get("close_time")
                    out.append(
                        {
                            "ticker": ticker,
                            "title": m.get("title") or "",
                            "event_ticker": m.get("event_ticker") or "",
                            "status": m.get("status") or "",
                            "yes_bid": yb,
                            "yes_ask": ya,
                            "volume": vol,
                            "close_time": close_time,
                        }
                    )
                cursor = data.get("cursor")
                if not cursor or not markets:
                    break

        out.sort(key=lambda x: (x.get("volume") or 0), reverse=True)
        trimmed = out[: settings.max_kalshi_markets]

        async with httpx.AsyncClient() as client:
            sem = asyncio.Semaphore(8)

            async def enrich(row: dict) -> None:
                async with sem:
                    try:
                        ob = await self.fetch_orderbook(client, row["ticker"])
                        yb2, ya2 = self._best_yes_from_orderbook(ob)
                        if yb2 is not None:
                            row["yes_bid"] = yb2
                        if ya2 is not None:
                            row["yes_ask"] = ya2
                    except Exception as e:  # noqa: BLE001
                        log.debug("kalshi orderbook %s: %s", row.get("ticker"), e)

            await asyncio.gather(*(enrich(r) for r in trimmed))
        return trimmed
