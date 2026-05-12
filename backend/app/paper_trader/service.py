from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KalshiMarket, MarketPair, PaperStatus, PaperTrade, PolyMarket


async def open_paper_trade(
    session: AsyncSession,
    pair_id: uuid.UUID,
    quantity: float,
) -> PaperTrade | None:
    res = await session.execute(
        select(MarketPair, KalshiMarket, PolyMarket)
        .join(KalshiMarket, MarketPair.kalshi_ticker == KalshiMarket.ticker)
        .join(PolyMarket, MarketPair.poly_condition_id == PolyMarket.condition_id)
        .where(MarketPair.id == pair_id)
    )
    row = res.first()
    if not row:
        return None
    pair, km, pm = row
    if km.yes_ask is None or pm.yes_bid is None or km.yes_bid is None or pm.yes_ask is None:
        return None
    ka, kb, pa, pb = float(km.yes_ask), float(km.yes_bid), float(pm.yes_ask), float(pm.yes_bid)
    kmid = (float(km.yes_bid or 0) + ka) / 2.0 if km.yes_bid is not None else ka
    pmid = (pb + pa) / 2.0
    legs = {
        "pair_id": str(pair.id),
        "snapshot": {
            "kalshi_yes_bid": kb,
            "kalshi_yes_ask": ka,
            "poly_yes_bid": pb,
            "poly_yes_ask": pa,
            "kalshi_mid": kmid,
            "poly_mid": pmid,
        },
    }
    entry_value = abs(kmid - pmid) * float(quantity)
    trade = PaperTrade(
        pair_id=pair_id,
        status=PaperStatus.open,
        legs=legs,
        quantity=quantity,
        entry_value=entry_value,
        mark_value=entry_value,
        realized_pnl=None,
    )
    session.add(trade)
    await session.flush()
    return trade


async def refresh_marks(session: AsyncSession) -> None:
    res = await session.execute(select(PaperTrade).where(PaperTrade.status == PaperStatus.open))
    open_trades = list(res.scalars().all())
    if not open_trades:
        return
    pair_ids = {t.pair_id for t in open_trades}
    p_res = await session.execute(select(MarketPair).where(MarketPair.id.in_(pair_ids)))
    pairs = {p.id: p for p in p_res.scalars().all()}
    k_res = await session.execute(select(KalshiMarket))
    kmap = {m.ticker: m for m in k_res.scalars().all()}
    p_res2 = await session.execute(select(PolyMarket))
    pmap = {m.condition_id: m for m in p_res2.scalars().all()}

    for t in open_trades:
        pair = pairs.get(t.pair_id)
        if not pair:
            continue
        km = kmap.get(pair.kalshi_ticker)
        pm = pmap.get(pair.poly_condition_id)
        if not km or not pm or km.yes_bid is None or km.yes_ask is None or pm.yes_bid is None or pm.yes_ask is None:
            continue
        ka, kb, pa, pb = float(km.yes_ask), float(km.yes_bid), float(pm.yes_ask), float(pm.yes_bid)
        kmid = (kb + ka) / 2.0
        pmid = (float(pm.yes_bid) + pa) / 2.0
        snap = t.legs.get("snapshot") if isinstance(t.legs, dict) else {}
        o_k = float(snap.get("kalshi_mid") or 0)
        o_p = float(snap.get("poly_mid") or 0)
        old_spread = abs(o_k - o_p)
        new_spread = abs(kmid - pmid)
        qty = float(t.quantity or 1)
        t.mark_value = max(0.0, (old_spread - new_spread)) * qty


async def close_paper_trade(session: AsyncSession, trade_id: uuid.UUID) -> PaperTrade | None:
    res = await session.execute(select(PaperTrade).where(PaperTrade.id == trade_id))
    t = res.scalar_one_or_none()
    if not t or t.status != PaperStatus.open:
        return None
    await refresh_marks(session)
    t.status = PaperStatus.closed
    t.closed_at = datetime.now(UTC)
    entry = float(t.entry_value or 0)
    mark = float(t.mark_value or 0)
    t.realized_pnl = mark - entry
    return t


async def list_portfolio(session: AsyncSession) -> list[dict[str, Any]]:
    await refresh_marks(session)
    res = await session.execute(select(PaperTrade).order_by(PaperTrade.opened_at.desc()).limit(200))
    rows = []
    for t in res.scalars():
        rows.append(
            {
                "id": str(t.id),
                "pair_id": str(t.pair_id),
                "status": t.status.value,
                "quantity": float(t.quantity),
                "entry_value": t.entry_value,
                "mark_value": t.mark_value,
                "realized_pnl": t.realized_pnl,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                "closed_at": t.closed_at.isoformat() if t.closed_at else None,
                "legs": t.legs,
            }
        )
    return rows
