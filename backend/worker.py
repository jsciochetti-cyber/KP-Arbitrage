"""Standalone ingestion worker for Render Background Worker (or local dev).

Run from backend/:  python worker.py
"""
from __future__ import annotations

import asyncio
import logging
import signal

import redis.asyncio as redis

from app.config import settings
from app.db.models import Base
from app.db.session import engine
from app.db.setup_timescale import ensure_timescale
from app.ingestion.service import IngestionService
from app.ingestion.ws_runner import run_poly_ws_loop

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def main() -> None:
    log.info("Starting ingestion worker (poll=%ss)", settings.kalshi_poll_seconds)
    r = redis.from_url(settings.redis_url, decode_responses=True)
    svc = IngestionService(r)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_timescale(engine)

    svc_ref: list[IngestionService] = [svc]

    def _shutdown() -> None:
        log.info("Shutdown signal received")
        svc_ref[0].stop()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass

    tasks = [
        asyncio.create_task(svc.run_loop(), name="ingestion"),
        asyncio.create_task(run_poly_ws_loop(r, svc), name="poly_ws"),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        svc.stop()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await r.close()
        await engine.dispose()
        log.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
