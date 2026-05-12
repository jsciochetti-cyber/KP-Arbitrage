from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import KalshiMarket, MarketPair, PolyMarket, PriceTick, Venue, WhaleTrade
from app.db.session import SessionLocal
from app.engine.arbitrage import compute_opportunities, persist_spread_snapshot
from app.engine.matching import auto_match_pairs
from app.ingestion.kalshi import KalshiClient
from app.ingestion.polymarket import PolymarketClient

log = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self.kalshi = KalshiClient()
        self.poly = PolymarketClient()
        self._redis: redis.Redis | None = redis_client
        self._poly_by_token: dict[str, dict] = {}
        self._stop = asyncio.Event()
        self._tick_counter = 0

    async def connect_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def _upsert_kalshi(self, session: AsyncSession, rows: list[dict]) -> None:
        for r in rows:
            stmt = insert(KalshiMarket).values(
                ticker=r["ticker"],
                title=r.get("title") or "",
                event_ticker=r.get("event_ticker") or "",
                status=r.get("status") or "",
                yes_bid=r.get("yes_bid"),
                yes_ask=r.get("yes_ask"),
                volume=r.get("volume"),
                close_time=_parse_dt(r.get("close_time")),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[KalshiMarket.ticker],
                set_={
                    "title": stmt.excluded.title,
                    "event_ticker": stmt.excluded.event_ticker,
                    "status": stmt.excluded.status,
                    "yes_bid": stmt.excluded.yes_bid,
                    "yes_ask": stmt.excluded.yes_ask,
                    "volume": stmt.excluded.volume,
                    "close_time": stmt.excluded.close_time,
                    "updated_at": datetime.now(UTC),
                },
            )
            await session.execute(stmt)

    async def _upsert_poly(self, session: AsyncSession, rows: list[dict]) -> None:
        for r in rows:
            cid = r.get("condition_id") or ""
            if not cid:
                continue
            stmt = insert(PolyMarket).values(
                condition_id=cid,
                question=r.get("question") or "",
                slug=r.get("slug") or "",
                token_yes=r.get("token_yes") or "",
                volume_24h=r.get("volume_24h"),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[PolyMarket.condition_id],
                set_={
                    "question": stmt.excluded.question,
                    "slug": stmt.excluded.slug,
                    "token_yes": stmt.excluded.token_yes,
                    "volume_24h": stmt.excluded.volume_24h,
                    "updated_at": datetime.now(UTC),
                },
            )
            await session.execute(stmt)

    async def _maybe_persist_ticks(
        self, session: AsyncSession, pairs: list[MarketPair], kmap: dict, pmap: dict
    ) -> None:
        self._tick_counter += 1
        if self._tick_counter % 3 != 0:
            return
        now = datetime.now(UTC)
        for p in pairs[:80]:
            kr = kmap.get(p.kalshi_ticker)
            pr = pmap.get(p.poly_condition_id)
            if kr and kr.get("yes_bid") is not None:
                session.add(
                    PriceTick(
                        pair_id=p.id,
                        venue=Venue.kalshi,
                        recorded_at=now,
                        yes_bid=kr.get("yes_bid"),
                        yes_ask=kr.get("yes_ask"),
                        volume=kr.get("volume"),
                    )
                )
            if pr and pr.get("yes_bid") is not None:
                session.add(
                    PriceTick(
                        pair_id=p.id,
                        venue=Venue.polymarket,
                        recorded_at=now,
                        yes_bid=pr.get("yes_bid"),
                        yes_ask=pr.get("yes_ask"),
                        volume=pr.get("volume_24h"),
                    )
                )

    async def _poll_kalshi_whale_trades(self, session: AsyncSession, tickers: list[str]) -> None:
        base = settings.kalshi_base_url.rstrip("/")
        async with httpx.AsyncClient() as client:
            for t in tickers[:40]:
                try:
                    r = await client.get(f"{base}/markets/trades", params={"ticker": t, "limit": 50}, timeout=20.0)
                    r.raise_for_status()
                    data = r.json()
                except Exception as e:  # noqa: BLE001
                    log.debug("kalshi trades %s: %s", t, e)
                    continue
                for tr in (data.get("trades") or [])[:5]:
                    try:
                        px = float(tr.get("yes_price_dollars") or 0)
                        cnt = float(tr.get("count_fp") or 0)
                    except (TypeError, ValueError):
                        continue
                    usd = abs(px * cnt)
                    if usd < settings.whale_min_usd:
                        continue
                    side = tr.get("taker_outcome_side") or tr.get("taker_side") or ""
                    wt = WhaleTrade(
                        id=uuid.uuid4(),
                        venue=Venue.kalshi,
                        market_ref=t,
                        side=str(side),
                        size_usd=usd,
                        price=px,
                        recorded_at=_parse_dt(tr.get("created_time")) or datetime.now(UTC),
                        raw=tr,
                    )
                    session.add(wt)

    async def _poly_whale_from_ws(self, session: AsyncSession, payload: dict) -> None:
        et = str(payload.get("event_type") or payload.get("type") or "")
        if "last_trade" not in et and payload.get("last_trade_price") is None:
            if payload.get("price") is None or payload.get("size") is None:
                return
        asset = str(payload.get("asset_id") or payload.get("asset") or "")
        if not asset:
            return
        try:
            price = float(payload.get("price") or payload.get("last_trade_price") or 0)
            size = float(payload.get("size") or 0)
        except (TypeError, ValueError):
            return
        usd = abs(price * size)
        if usd < settings.whale_min_usd:
            return
        m = self._poly_by_token.get(asset) or {}
        cid = m.get("condition_id") or asset
        wt = WhaleTrade(
            id=uuid.uuid4(),
            venue=Venue.polymarket,
            market_ref=cid,
            side=str(payload.get("side") or ""),
            size_usd=usd,
            price=price,
            recorded_at=datetime.now(UTC),
            raw=payload,
        )
        session.add(wt)

    async def on_poly_ws(self, payload: dict) -> None:
        et = str(payload.get("event_type") or payload.get("type") or "")
        asset = str(payload.get("asset_id") or "")
        if et.endswith("best_bid_ask") or ("best_bid" in payload and "best_ask" in payload):
            if not asset:
                return
            try:
                bid = float(payload.get("best_bid") or payload.get("bid") or 0)
                ask = float(payload.get("best_ask") or payload.get("ask") or 0)
            except (TypeError, ValueError):
                return
            m = self._poly_by_token.get(asset)
            if m:
                if bid:
                    m["yes_bid"] = bid
                if ask:
                    m["yes_ask"] = ask
        if "last_trade" in et or (payload.get("price") is not None and payload.get("size") is not None):
            async with SessionLocal() as session:
                try:
                    await self._poly_whale_from_ws(session, payload)
                    await session.commit()
                except Exception as e:  # noqa: BLE001
                    log.debug("whale ws commit: %s", e)
                    await session.rollback()

    async def run_loop(self) -> None:
        r = await self.connect_redis()
        while not self._stop.is_set():
            try:
                k_rows = await self.kalshi.sync_markets_snapshot()
                p_rows = await self.poly.fetch_active_markets()
                await self.poly.refresh_prices_rest(p_rows)
                self._poly_by_token = {m["token_yes"]: m for m in p_rows if m.get("token_yes")}

                async with SessionLocal() as session:
                    await self._upsert_kalshi(session, k_rows)
                    await self._upsert_poly(session, p_rows)
                    await session.commit()

                    await auto_match_pairs(session)
                    await session.commit()

                    res = await session.execute(select(MarketPair))
                    pairs = list(res.scalars().all())

                    kmap = {x["ticker"]: x for x in k_rows}
                    pmap = {x["condition_id"]: x for x in p_rows}

                    await self._maybe_persist_ticks(session, pairs, kmap, pmap)
                    opps = await compute_opportunities(session, pairs, kmap, pmap)
                    await persist_spread_snapshot(session, opps)
                    await self._poll_kalshi_whale_trades(session, [x["ticker"] for x in k_rows])
                    await session.commit()

                await r.set("arb:opportunities", json.dumps(opps), ex=120)
                await r.publish("arb_updates", json.dumps({"ts": datetime.now(UTC).isoformat(), "n": len(opps)}))

                await r.set("cache:k_rows", json.dumps(k_rows[:400]), ex=120)
                await r.set("cache:p_rows", json.dumps(p_rows[:400]), ex=120)
            except Exception as e:  # noqa: BLE001
                log.exception("ingestion cycle error: %s", e)

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=settings.kalshi_poll_seconds)
            except asyncio.TimeoutError:
                continue
            break

    def stop(self) -> None:
        self._stop.set()


def _parse_dt(v: Any) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    if isinstance(v, str):
        try:
            s = v.replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None
