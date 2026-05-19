from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from thefuzz import fuzz
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.models import KalshiMarket, MarketPair, PolyMarket, PriceTick, Spread, WhaleTrade
from app.paper_trader.service import close_paper_trade, list_portfolio, open_paper_trade

router = APIRouter(prefix="/v1")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/arb")
async def get_arb(request: Request) -> list[dict[str, Any]]:
    r = request.app.state.redis
    raw = await r.get("arb:opportunities")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


@router.get("/pairs")
async def list_pairs(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    res = await session.execute(select(MarketPair))
    pairs = list(res.scalars().all())
    out = []
    for p in pairs:
        out.append(
            {
                "id": str(p.id),
                "kalshi_ticker": p.kalshi_ticker,
                "poly_condition_id": p.poly_condition_id,
                "match_score": p.match_score,
                "manual": p.manual,
            }
        )
    return out


@router.get("/spreads/{pair_id}")
async def get_spreads(
    pair_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(500, ge=1, le=5000),
) -> list[dict[str, Any]]:
    res = await session.execute(
        select(Spread).where(Spread.pair_id == pair_id).order_by(desc(Spread.recorded_at)).limit(limit)
    )
    rows = []
    for s in res.scalars():
        rows.append(
            {
                "recorded_at": s.recorded_at.isoformat(),
                "spread_pct": s.spread_pct,
                "arb_type": s.arb_type.value,
                "best_edge": s.best_edge,
                "meta": s.meta,
            }
        )
    return rows


@router.get("/history/{pair_id}")
async def get_history(
    pair_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(2000, ge=1, le=10000),
) -> list[dict[str, Any]]:
    res = await session.execute(
        select(PriceTick).where(PriceTick.pair_id == pair_id).order_by(desc(PriceTick.recorded_at)).limit(limit)
    )
    rows = []
    for t in res.scalars():
        rows.append(
            {
                "recorded_at": t.recorded_at.isoformat(),
                "venue": t.venue.value,
                "yes_bid": float(t.yes_bid) if t.yes_bid is not None else None,
                "yes_ask": float(t.yes_ask) if t.yes_ask is not None else None,
                "volume": float(t.volume) if t.volume is not None else None,
            }
        )
    return rows


@router.get("/search")
async def search_markets(
    q: str = Query(..., min_length=2),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(25, ge=1, le=100),
) -> dict[str, Any]:
    ql = q.lower()
    k_res = await session.execute(select(KalshiMarket).limit(800))
    p_res = await session.execute(select(PolyMarket).limit(800))
    k_hits: list[tuple[float, KalshiMarket]] = []
    for km in k_res.scalars():
        title = (km.title or "").lower()
        if not title:
            continue
        score = float(fuzz.token_set_ratio(ql, title))
        if score >= 75:
            k_hits.append((score, km))
    p_hits: list[tuple[float, PolyMarket]] = []
    for pm in p_res.scalars():
        question = (pm.question or "").lower()
        if not question:
            continue
        score = float(fuzz.token_set_ratio(ql, question))
        if score >= 75:
            p_hits.append((score, pm))
    k_hits.sort(key=lambda x: x[0], reverse=True)
    p_hits.sort(key=lambda x: x[0], reverse=True)
    return {
        "query": q,
        "kalshi": [
            {
                "ticker": m.ticker,
                "title": m.title,
                "score": sc,
                "yes_bid": float(m.yes_bid) if m.yes_bid is not None else None,
                "yes_ask": float(m.yes_ask) if m.yes_ask is not None else None,
            }
            for sc, m in k_hits[:limit]
        ],
        "polymarket": [
            {
                "condition_id": m.condition_id,
                "question": m.question,
                "slug": m.slug,
                "score": sc,
            }
            for sc, m in p_hits[:limit]
        ],
    }


@router.get("/volume")
async def volume_dashboard(request: Request) -> dict[str, Any]:
    r = request.app.state.redis
    raw_k = await r.get("cache:k_rows")
    raw_p = await r.get("cache:p_rows")
    k_rows = json.loads(raw_k) if raw_k else []
    p_rows = json.loads(raw_p) if raw_p else []
    k_vol = sum(float(x.get("volume") or 0) for x in k_rows)
    p_vol = sum(float(x.get("volume_24h") or 0) for x in p_rows)
    top_k = sorted(k_rows, key=lambda x: float(x.get("volume") or 0), reverse=True)[:15]
    top_p = sorted(p_rows, key=lambda x: float(x.get("volume_24h") or 0), reverse=True)[:15]
    cache_ts = await r.get("cache:ingestion_ts")
    return {
        "updated_at": cache_ts,
        "totals": {
            "kalshi_volume_sum": k_vol,
            "polymarket_24h_volume_sum": p_vol,
            "ratio_kalshi_to_poly": (k_vol / p_vol) if p_vol else None,
            "kalshi_open_interest_volume_sum": k_vol,
        },
        "top_kalshi": [{"ticker": x.get("ticker"), "title": x.get("title"), "volume": x.get("volume")} for x in top_k],
        "top_polymarket": [
            {"condition_id": x.get("condition_id"), "question": x.get("question"), "volume_24h": x.get("volume_24h")}
            for x in top_p
        ],
    }


@router.get("/whales")
async def list_whales(
    session: AsyncSession = Depends(get_session),
    min_usd: float = Query(500, ge=1),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    since = datetime.now(UTC) - timedelta(hours=48)
    res = await session.execute(
        select(WhaleTrade)
        .where(WhaleTrade.size_usd >= min_usd, WhaleTrade.recorded_at >= since)
        .order_by(desc(WhaleTrade.recorded_at))
        .limit(limit)
    )
    trades = list(res.scalars())
    k_refs = {w.market_ref for w in trades if w.venue.value == "kalshi"}
    p_refs = {w.market_ref for w in trades if w.venue.value == "polymarket"}
    k_titles: dict[str, str] = {}
    p_titles: dict[str, str] = {}
    if k_refs:
        k_res = await session.execute(select(KalshiMarket).where(KalshiMarket.ticker.in_(k_refs)))
        for km in k_res.scalars():
            k_titles[km.ticker] = km.title or km.ticker
    if p_refs:
        p_res = await session.execute(select(PolyMarket).where(PolyMarket.condition_id.in_(p_refs)))
        for pm in p_res.scalars():
            p_titles[pm.condition_id] = pm.question or pm.condition_id

    rows = []
    for w in trades:
        if w.venue.value == "kalshi":
            market_title = k_titles.get(w.market_ref, w.market_ref)
        else:
            market_title = p_titles.get(w.market_ref, w.market_ref)
        rows.append(
            {
                "id": str(w.id),
                "venue": w.venue.value,
                "market_ref": w.market_ref,
                "market_title": market_title,
                "side": w.side or "",
                "size_usd": w.size_usd,
                "price": w.price,
                "recorded_at": w.recorded_at.isoformat(),
            }
        )
    return rows


class PaperOrderBody(BaseModel):
    pair_id: uuid.UUID
    quantity: float = Field(default=1.0, gt=0, le=1_000_000)


@router.post("/paper/orders")
async def paper_order(body: PaperOrderBody, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    t = await open_paper_trade(session, body.pair_id, body.quantity)
    if not t:
        raise HTTPException(status_code=400, detail="Unable to open paper trade (missing pair or prices)")
    await session.commit()
    return {"id": str(t.id), "status": t.status.value}


@router.post("/paper/orders/{trade_id}/close")
async def paper_close(trade_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    t = await close_paper_trade(session, trade_id)
    if not t:
        raise HTTPException(status_code=404, detail="Trade not found or not open")
    await session.commit()
    return {"id": str(t.id), "status": t.status.value, "realized_pnl": t.realized_pnl}


@router.get("/paper/portfolio")
async def paper_portfolio(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    rows = await list_portfolio(session)
    await session.commit()
    return rows


@router.websocket("/ws")
async def arb_stream(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            r = ws.app.state.redis
            raw = await r.get("arb:opportunities")
            await ws.send_text(raw or "[]")
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        return

