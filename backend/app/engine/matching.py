from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rapidfuzz import fuzz

from app.db.models import KalshiMarket, MarketPair, PolyMarket


async def auto_match_pairs(session: AsyncSession, max_k: int = 120, max_p: int = 150, min_score: float = 72.0) -> int:
    """Fuzzy match Kalshi ↔ Polymarket titles; insert new MarketPair rows."""
    k_res = await session.execute(select(KalshiMarket))
    p_res = await session.execute(select(PolyMarket))
    ks = list(k_res.scalars())[:max_k]
    ps = list(p_res.scalars())[:max_p]

    ex_res = await session.execute(select(MarketPair.kalshi_ticker, MarketPair.poly_condition_id))
    ex_pairs = {(a, b) for a, b in ex_res.all()}

    created = 0
    for km in ks:
        if not km.title:
            continue
        best_score = 0.0
        best_pm: PolyMarket | None = None
        kt = km.title.lower()
        for pm in ps:
            if not pm.question:
                continue
            score = float(fuzz.token_set_ratio(kt, pm.question.lower()))
            if score > best_score:
                best_score = score
                best_pm = pm
        if best_pm and best_score >= min_score:
            key = (km.ticker, best_pm.condition_id)
            if key in ex_pairs:
                continue
            session.add(
                MarketPair(
                    kalshi_ticker=km.ticker,
                    poly_condition_id=best_pm.condition_id,
                    match_score=best_score,
                    manual=False,
                )
            )
            ex_pairs.add(key)
            created += 1
    return created
