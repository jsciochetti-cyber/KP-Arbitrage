from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://arb:arb@localhost:5432/arb"
    redis_url: str = "redis://localhost:6379/0"

    kalshi_base_url: str = "https://external-api.kalshi.com/trade-api/v2"
    poly_gamma_url: str = "https://gamma-api.polymarket.com"
    poly_clob_url: str = "https://clob.polymarket.com"
    poly_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    poly_subgraph_url: str | None = None

    cors_origins: str = "http://localhost:3000"

    kalshi_poll_seconds: float = 15.0
    poly_gamma_refresh_seconds: float = 120.0
    max_kalshi_markets: int = 150
    max_poly_markets: int = 80
    whale_min_usd: float = 500.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
