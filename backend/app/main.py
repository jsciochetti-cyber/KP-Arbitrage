import asyncio
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
from app.ingestion.service import IngestionService
from app.ingestion.ws_runner import run_poly_ws_loop

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.ingest = IngestionService(app.state.redis)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_timescale(engine)
    tasks: list[asyncio.Task[None]] = []
    if not settings.disable_ingestion:
        tasks = [
            asyncio.create_task(app.state.ingest.run_loop(), name="ingestion"),
            asyncio.create_task(run_poly_ws_loop(app.state.redis, app.state.ingest), name="poly_ws"),
        ]
        log.info("Ingestion tasks started in API process")
    else:
        log.info("Ingestion disabled in API process (use worker.py)")
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
