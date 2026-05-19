from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as redis

from app.ingestion.polymarket import PolymarketClient
from app.ingestion.service import IngestionService

log = logging.getLogger(__name__)


async def run_poly_ws_loop(r: redis.Redis, ingest: IngestionService) -> None:
    poly = PolymarketClient()
    while True:
        try:
            raw = await r.get("cache:p_rows")
            tokens: list[str] = []
            if raw:
                for row in json.loads(raw):
                    t = row.get("token_yes")
                    if t:
                        tokens.append(str(t))
            if not tokens:
                await asyncio.sleep(10)
                continue
            await poly.ws_best_bid_ask_loop(tokens[:60], ingest.on_poly_ws)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            log.warning("poly ws runner: %s", e)
            await asyncio.sleep(5)
