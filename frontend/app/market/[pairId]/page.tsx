"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiGet } from "@/lib/api";

type ArbRow = {
  pair_id: string;
  kalshi_ticker: string;
  poly_condition_id: string;
  title_k?: string;
  title_p?: string;
  kalshi_yes_bid: number;
  kalshi_yes_ask: number;
  poly_yes_bid: number;
  poly_yes_ask: number;
};

type SpreadRow = { recorded_at: string; spread_pct: number; best_edge: number | null };
type HistRow = { recorded_at: string; venue: string; yes_bid: number | null; yes_ask: number | null };

export default function MarketPage() {
  const params = useParams<{ pairId: string }>();
  const pairId = String(params?.pairId || "");
  const [arb, setArb] = useState<ArbRow | null>(null);
  const [spreads, setSpreads] = useState<SpreadRow[]>([]);
  const [hist, setHist] = useState<HistRow[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    try {
      const all = await apiGet<ArbRow[]>("/v1/arb");
      const row = all.find((x) => x.pair_id === pairId) || null;
      setArb(row);
      const s = await apiGet<SpreadRow[]>(`/v1/spreads/${pairId}?limit=500`);
      setSpreads([...s].reverse());
      const h = await apiGet<HistRow[]>(`/v1/history/${pairId}?limit=5000`);
      setHist([...h].reverse());
      setErr(null);
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  useEffect(() => {
    if (!pairId) return;
    load();
    const id = window.setInterval(load, 8000);
    return () => window.clearInterval(id);
  }, [pairId]);

  const midsSeries = useMemo(() => {
    const byTs = new Map<string, { t: string; k?: number; p?: number }>();
    for (const row of hist) {
      const t = row.recorded_at;
      const cur = byTs.get(t) || { t };
      const mid =
        row.yes_bid != null && row.yes_ask != null ? (row.yes_bid + row.yes_ask) / 2 : row.yes_bid ?? row.yes_ask;
      if (mid == null) continue;
      if (row.venue === "kalshi") cur.k = mid;
      if (row.venue === "polymarket") cur.p = mid;
      byTs.set(t, cur);
    }
    return Array.from(byTs.values())
      .filter((x) => x.k != null || x.p != null)
      .slice(-300);
  }, [hist]);

  if (!pairId) {
    return <div className="text-sm text-zinc-500">Loading…</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-sm text-zinc-400">
            <Link href="/scanner" className="hover:underline">
              Scanner
            </Link>{" "}
            / Market
          </div>
          <h1 className="text-xl font-semibold mt-1">Market differences</h1>
          <p className="text-xs text-zinc-500 font-mono mt-2">{pairId}</p>
        </div>
        <button className="text-sm rounded-lg border border-zinc-700 px-3 py-2 hover:bg-zinc-900" onClick={load}>
          Refresh
        </button>
      </div>

      {err ? <div className="text-sm text-red-400">{err}</div> : null}

      {arb ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-zinc-800 p-4">
            <div className="text-sm text-zinc-400">Kalshi</div>
            <div className="font-mono text-xs mt-2 text-zinc-300">{arb.kalshi_ticker}</div>
            <div className="mt-2 text-zinc-200">{arb.title_k}</div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <Stat label="YES bid" v={arb.kalshi_yes_bid} />
              <Stat label="YES ask" v={arb.kalshi_yes_ask} />
            </div>
          </div>
          <div className="rounded-xl border border-zinc-800 p-4">
            <div className="text-sm text-zinc-400">Polymarket</div>
            <div className="font-mono text-xs mt-2 text-zinc-300">{arb.poly_condition_id}</div>
            <div className="mt-2 text-zinc-200">{arb.title_p}</div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <Stat label="YES bid" v={arb.poly_yes_bid} />
              <Stat label="YES ask" v={arb.poly_yes_ask} />
            </div>
          </div>
        </div>
      ) : (
        <div className="text-sm text-zinc-500">
          No live snapshot for this pair in <code>/v1/arb</code> yet. Open a pair id from the scanner table.
        </div>
      )}

      <div className="rounded-xl border border-zinc-800 p-4 h-[320px]">
        <div className="text-sm text-zinc-400 mb-3">Spread history (%)</div>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={spreads}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis dataKey="recorded_at" tick={{ fill: "#a1a1aa", fontSize: 10 }} minTickGap={24} />
            <YAxis tick={{ fill: "#a1a1aa", fontSize: 10 }} />
            <Tooltip contentStyle={{ background: "#09090b", border: "1px solid #27272a" }} />
            <Legend />
            <Line type="monotone" dataKey="spread_pct" name="spread %" stroke="#60a5fa" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-xl border border-zinc-800 p-4 h-[320px]">
        <div className="text-sm text-zinc-400 mb-3">YES mids (sampled ticks)</div>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={midsSeries}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis dataKey="t" tick={{ fill: "#a1a1aa", fontSize: 10 }} minTickGap={24} />
            <YAxis domain={[0, 1]} tick={{ fill: "#a1a1aa", fontSize: 10 }} />
            <Tooltip contentStyle={{ background: "#09090b", border: "1px solid #27272a" }} />
            <Legend />
            <Line type="monotone" dataKey="k" name="kalshi mid" stroke="#34d399" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="p" name="poly mid" stroke="#fbbf24" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Stat({ label, v }: { label: string; v: number }) {
  return (
    <div className="rounded-lg bg-zinc-900/40 border border-zinc-800 p-3">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="tabular-nums mt-1">{Number(v).toFixed(4)}</div>
    </div>
  );
}
