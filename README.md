# KP-Arbitrage

# Kalshi × Polymarket Arbitrage System

Internal tool: live cross-venue prices, arbitrage scanner, paper trading, whale feed, and REST/WebSocket APIs.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- **API**: http://localhost:8000/docs  
- **UI**: http://localhost:3000  

### Local dev (without Docker for Node/Python)

1. Start DB + Redis only:

   ```bash
   docker compose up -d db redis
   ```

2. Backend:

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   set DATABASE_URL=postgresql+asyncpg://arb:arb@localhost:5432/arb
   set REDIS_URL=redis://localhost:6379/0
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. Frontend:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Render deployment (production)

1. **Web Service** (API): `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
   - Set `DATABASE_URL`, `REDIS_URL`, `CORS_ORIGINS=https://your-app.vercel.app`  
   - Set `DISABLE_INGESTION=true` so only the worker runs polling  

2. **Background Worker**: start command `python worker.py` (root: `backend/`)  
   - Same `DATABASE_URL` and `REDIS_URL`  
   - Do **not** set `DISABLE_INGESTION`  

3. **Vercel** (frontend): `NEXT_PUBLIC_API_URL=https://your-api.onrender.com`  

If you add new DB columns (e.g. `whale_trades.external_id`), run a migration on Supabase or recreate tables in dev.

## Notes

- Kalshi public REST is used for markets + orderbooks (no API key required for read-only market data).
- Polymarket uses Gamma for market metadata and CLOB REST/WebSocket for prices. Configure `POLY_SUBGRAPH_URL` for deeper on-chain whale indexing; without it, whale detection uses CLOB recent trades when available.
- Paper trading executes against last-seen mid prices stored in Redis/DB.
