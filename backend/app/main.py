import asyncio
import json
import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.config import settings
from app.db.models import Base
from app.db.session import engine
from app.db.setup_timescale import ensure_timescale
from app.ingestion.polymarket import PolymarketClient
from app.ingestion.service import IngestionService

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def run_poly_ws(app: FastAPI) -> None:
    poly = PolymarketClient()
    while True:
        try:
            r = app.state.redis
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
            svc: IngestionService = app.state.ingest
            await poly.ws_best_bid_ask_loop(tokens[:60], svc.on_poly_ws)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            log.warning("poly ws runner: %s", e)
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.ingest = IngestionService(app.state.redis)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_timescale(engine)
    tasks = [
        asyncio.create_task(app.state.ingest.run_loop(), name="ingestion"),
        asyncio.create_task(run_poly_ws(app), name="poly_ws"),
    ]
    app.state.tasks = tasks
    try:
        yield
    finally:
        app.state.ingest.stop()
        for t in tasks:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        await app.state.redis.close()
        await engine.dispose()


app = FastAPI(title="Kalshi × Polymarket Arb", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"docs": "/docs", "api": "/v1/health"}
