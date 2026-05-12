from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import websockets

from app.config import settings

log = logging.getLogger(__name__)


class PolymarketClient:
    def __init__(self) -> None:
        self.gamma = settings.poly_gamma_url.rstrip("/")
        self.clob = settings.poly_clob_url.rstrip("/")
        self.ws_url = settings.poly_ws_url

    async def fetch_active_markets(self) -> list[dict]:
        """Gamma markets list (active, tradable)."""
        rows: list[dict] = []
        offset = 0
        limit = 100
        async with httpx.AsyncClient() as client:
            while len(rows) < settings.max_poly_markets + limit:
                r = await client.get(
                    f"{self.gamma}/markets",
                    params={
                        "active": "true",
                        "closed": "false",
                        "limit": limit,
                        "offset": offset,
                    },
                    timeout=45.0,
                )
                r.raise_for_status()
                batch = r.json()
                if not batch:
                    break
                for m in batch:
                    if not m.get("active") or m.get("closed"):
                        continue
                    tokens = m.get("clobTokenIds")
                    if isinstance(tokens, str):
                        try:
                            tokens = json.loads(tokens)
                        except json.JSONDecodeError:
                            tokens = None
                    if not tokens or not isinstance(tokens, list):
                        continue
                    tid_yes = str(tokens[0])
                    tid_no = str(tokens[1]) if len(tokens) > 1 else ""
                    rows.append(
                        {
                            "condition_id": m.get("conditionId") or m.get("id") or "",
                            "question": m.get("question") or m.get("title") or "",
                            "slug": m.get("slug") or "",
                            "token_yes": tid_yes,
                            "token_no": tid_no,
                            "volume_24h": float(m.get("volume24hr") or m.get("volume24hrClob") or 0) or 0.0,
                        }
                    )
                offset += limit
                if len(batch) < limit:
                    break
        rows.sort(key=lambda x: x.get("volume_24h") or 0, reverse=True)
        return rows[: settings.max_poly_markets]

    async def fetch_book_mid(self, client: httpx.AsyncClient, token_id: str) -> tuple[float | None, float | None, float | None]:
        """Return best bid, best ask, mid for YES token."""
        try:
            r = await client.get(f"{self.clob}/book", params={"token_id": token_id}, timeout=20.0)
            r.raise_for_status()
            data = r.json()
        except Exception as e:  # noqa: BLE001
            log.debug("poly book %s: %s", token_id[:8], e)
            return None, None, None
        bids = data.get("bids") or []
        asks = data.get("asks") or []
        try:
            best_bid = float(bids[0]["price"]) if bids else None
        except (KeyError, IndexError, TypeError, ValueError):
            best_bid = None
        try:
            best_ask = float(asks[0]["price"]) if asks else None
        except (KeyError, IndexError, TypeError, ValueError):
            best_ask = None
        mid = None
        if best_bid is not None and best_ask is not None:
            mid = (best_bid + best_ask) / 2.0
        elif best_bid is not None:
            mid = best_bid
        elif best_ask is not None:
            mid = best_ask
        return best_bid, best_ask, mid

    async def refresh_prices_rest(self, markets: list[dict]) -> None:
        sem = asyncio.Semaphore(10)

        async def one(client: httpx.AsyncClient, m: dict) -> None:
            async with sem:
                bid, ask, _mid = await self.fetch_book_mid(client, m["token_yes"])
                m["yes_bid"] = bid
                m["yes_ask"] = ask

        async with httpx.AsyncClient() as client:
            await asyncio.gather(*(one(client, m) for m in markets))

    async def ws_best_bid_ask_loop(self, token_ids: list[str], on_update: Any) -> None:
        """Maintain WS connection; invoke callback with dict updates."""
        if not token_ids:
            return
        chunk_size = 40
        while True:
            try:
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=20) as ws:
                    for i in range(0, len(token_ids), chunk_size):
                        chunk = token_ids[i : i + chunk_size]
                        msg = {
                            "assets_ids": chunk,
                            "type": "market",
                            "custom_feature_enabled": True,
                        }
                        await ws.send(json.dumps(msg))
                    async for raw in ws:
                        if isinstance(raw, bytes):
                            raw = raw.decode()
                        try:
                            payload = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(payload, dict):
                            await on_update(payload)
                        elif isinstance(payload, list):
                            for item in payload:
                                if isinstance(item, dict):
                                    await on_update(item)
            except Exception as e:  # noqa: BLE001
                log.warning("poly ws reconnecting: %s", e)
                await asyncio.sleep(2.0)
