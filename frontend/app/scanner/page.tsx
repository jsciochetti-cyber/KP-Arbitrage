"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiGet, parseApiError, wsUrl } from "@/lib/api";

type ArbRow = {
  pair_id: string;
  kalshi_ticker: string;
  poly_condition_id: string;
  title_k?: string;
  title_p?: string;
  spread_pct: number;
  implied_edge: number;
  round_trip_edge: number;
  arb_type: string;
  volume_kalshi: number;
  volume_poly_24h: number;
  close_time?: string | null;
};

export default function ScannerPage() {
  const [rows, setRows] = useState<ArbRow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const data = await apiGet<ArbRow[]>("/v1/arb");
      setRows(data);
      setErr(null);
    } catch (e) {
      setErr(parseApiError(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 8000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl());
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as ArbRow[];
          if (Array.isArray(data)) setRows(data);
        } catch {
          // ignore
        }
      };
    } catch {
      // ignore
    }
    return () => ws?.close();
  }, []);

  const sorted = useMemo(() => [...rows].sort((a, b) => (b.spread_pct ?? 0) - (a.spread_pct ?? 0)), [rows]);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Arbitrage scanner</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Ranked by cross-venue mid spread. REST polling (8s) + WebSocket push.
          </p>
        </div>
        <button
          onClick={() => refresh()}
          className="text-sm rounded-lg border border-zinc-700 px-3 py-2 hover:bg-zinc-900"
        >
          Refresh
        </button>
      </div>

      {err ? <div className="text-sm text-red-400">Backend: {err}</div> : null}

      {loading && sorted.length === 0 ? (
        <div className="animate-pulse rounded-xl border border-zinc-800 h-48 bg-zinc-900/50" />
      ) : null}

      <div className="overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="text-left text-zinc-400 border-b border-zinc-800">
            <tr>
              <th className="p-3">Pair</th>
              <th className="p-3 hidden sm:table-cell">Kalshi</th>
              <th className="p-3 hidden sm:table-cell">Polymarket</th>
              <th className="p-3">Spread %</th>
              <th className="p-3 hidden md:table-cell">Edge</th>
              <th className="p-3 hidden md:table-cell">RT edge</th>
              <th className="p-3 hidden lg:table-cell">Vol</th>
              <th className="p-3 hidden lg:table-cell">Match</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.pair_id} className="border-b border-zinc-900 hover:bg-zinc-900/40">
                <td className="p-3">
                  <Link className="text-blue-300 hover:underline" href={`/market/${r.pair_id}`}>
                    Drill in
                  </Link>
                  <div className="text-xs text-zinc-500 mt-1 font-mono truncate max-w-[140px]">{r.pair_id}</div>
                </td>
                <td className="p-3 hidden sm:table-cell">
                  <div className="font-mono text-xs text-zinc-300">{r.kalshi_ticker}</div>
                  <div className="text-zinc-400 line-clamp-2">{r.title_k}</div>
                </td>
                <td className="p-3 hidden sm:table-cell">
                  <div className="font-mono text-xs text-zinc-300 truncate max-w-[120px]">{r.poly_condition_id}</div>
                  <div className="text-zinc-400 line-clamp-2">{r.title_p}</div>
                </td>
                <td className="p-3 tabular-nums">{r.spread_pct?.toFixed(2)}</td>
                <td className="p-3 tabular-nums hidden md:table-cell">{r.implied_edge?.toFixed(4)}</td>
                <td className="p-3 tabular-nums hidden md:table-cell">{r.round_trip_edge?.toFixed(4)}</td>
                <td className="p-3 tabular-nums text-xs hidden lg:table-cell">
                  {Number(r.volume_kalshi || 0).toFixed(0)} / {Number(r.volume_poly_24h || 0).toFixed(0)}
                </td>
                <td className="p-3 text-xs text-zinc-400 hidden lg:table-cell">{r.arb_type}</td>
              </tr>
            ))}
            {!loading && sorted.length === 0 ? (
              <tr>
                <td className="p-6 text-zinc-500" colSpan={8}>
                  No opportunities yet. Ensure the ingestion worker is running on Render.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}