from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def ensure_timescale(engine: AsyncEngine) -> None:
    """Enable TimescaleDB and convert tick/spread tables to hypertables if possible."""
    stmts = [
        "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;",
        """
        SELECT public.create_hypertable(
            'price_ticks', 'recorded_at',
            if_not_exists => TRUE
        );
        """,
        """
        SELECT public.create_hypertable(
            'spreads', 'recorded_at',
            if_not_exists => TRUE
        );
        """,
    ]
    async with engine.begin() as conn:
        for sql in stmts:
            try:
                await conn.execute(text(sql))
            except Exception:
                # Hypertable may already exist or extension missing in dev DB
                pass
