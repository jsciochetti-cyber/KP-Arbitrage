from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ArbType, MarketPair, Spread


async def compute_opportunities(
    _session: AsyncSession,
    pairs: list[MarketPair],
    kmap: dict[str, dict],
    pmap: dict[str, dict],
) -> list[dict[str, Any]]:
    """Rank cross-venue dislocations for matched pairs."""
    out: list[dict[str, Any]] = []
    for p in pairs:
        k = kmap.get(p.kalshi_ticker)
        poly = pmap.get(p.poly_condition_id)
        if not k or not poly:
            continue
        kb, ka = k.get("yes_bid"), k.get("yes_ask")
        pb, pa = poly.get("yes_bid"), poly.get("yes_ask")
        if kb is None or ka is None or pb is None or pa is None:
            continue
        try:
            kb_f, ka_f, pb_f, pa_f = float(kb), float(ka), float(pb), float(pa)
        except (TypeError, ValueError):
            continue
        kmid = (kb_f + ka_f) / 2.0
        pmid = (pb_f + pa_f) / 2.0
        denom = max(0.02, min(kmid, 1.0 - kmid, pmid, 1.0 - pmid))
        spread_pct = abs(kmid - pmid) / denom * 100.0
        edge = abs(kmid - pmid)

        # Rough round-trip: buy YES Kalshi + synthetic hedge using Polymarket YES bid as NO sell proxy
        cost_rt = ka_f + max(0.0, 1.0 - pb_f)
        round_trip_edge = 1.0 - cost_rt

        vol_k = float(k.get("volume") or 0)
        vol_p = float(poly.get("volume_24h") or 0)

        close_time = k.get("close_time")

        arb_type = ArbType.cross_venue_yes
        best_edge = edge
        if round_trip_edge > edge and round_trip_edge > 0:
            arb_type = ArbType.round_trip
            best_edge = float(round_trip_edge)

        out.append(
            {
                "pair_id": str(p.id),
                "kalshi_ticker": p.kalshi_ticker,
                "poly_condition_id": p.poly_condition_id,
                "title_k": k.get("title"),
                "title_p": poly.get("question"),
                "match_score": p.match_score,
                "kalshi_yes_bid": kb_f,
                "kalshi_yes_ask": ka_f,
                "poly_yes_bid": pb_f,
                "poly_yes_ask": pa_f,
                "spread_pct": float(spread_pct),
                "implied_edge": float(edge),
                "round_trip_edge": float(round_trip_edge),
                "arb_type": arb_type.value,
                "volume_kalshi": vol_k,
                "volume_poly_24h": vol_p,
                "close_time": close_time,
            }
        )

    out.sort(key=lambda x: x.get("spread_pct") or 0, reverse=True)
    return out


async def persist_spread_snapshot(session: AsyncSession, opps: list[dict[str, Any]]) -> None:
    """Store top spread rows for history API."""
    now = datetime.now(UTC)
    for row in opps[:50]:
        try:
            pid = uuid.UUID(str(row["pair_id"]))
        except (KeyError, ValueError):
            continue
        at = ArbType.cross_venue_yes
        if row.get("arb_type") == ArbType.round_trip.value:
            at = ArbType.round_trip
        session.add(
            Spread(
                pair_id=pid,
                recorded_at=now,
                spread_pct=float(row.get("spread_pct") or 0),
                arb_type=at,
                best_edge=float(row.get("implied_edge") or 0),
                meta={
                    "round_trip_edge": row.get("round_trip_edge"),
                    "kalshi_yes_bid": row.get("kalshi_yes_bid"),
                    "poly_yes_bid": row.get("poly_yes_bid"),
                },
            )
        )
