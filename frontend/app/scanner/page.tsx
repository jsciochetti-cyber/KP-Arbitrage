"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiGet, wsUrl } from "@/lib/api";

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

  const refresh = async () => {
    try {
      const data = await apiGet<ArbRow[]>("/v1/arb");
      setRows(data);
      setErr(null);
    } catch (e) {
      setErr((e as Error).message);
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
      ws.onerror = () => {
        // handled by polling
      };
    } catch {
      // ignore
    }
    return () => {
      ws?.close();
    };
  }, []);

  const sorted = useMemo(() => [...rows].sort((a, b) => (b.spread_pct ?? 0) - (a.spread_pct ?? 0)), [rows]);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Arbitrage scanner</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Ranked by cross-venue mid spread. Updates via WebSocket (2s) + REST fallback.
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

      <div className="overflow-auto rounded-xl border border-zinc-800">
        <table className="min-w-[1100px] w-full text-sm">
          <thead className="text-left text-zinc-400 border-b border-zinc-800">
            <tr>
              <th className="p-3">Pair</th>
              <th className="p-3">Kalshi</th>
              <th className="p-3">Polymarket</th>
              <th className="p-3">Spread %</th>
              <th className="p-3">Edge</th>
              <th className="p-3">RT edge</th>
              <th className="p-3">Vol K / Vol P</th>
              <th className="p-3">Match</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.pair_id} className="border-b border-zinc-900 hover:bg-zinc-900/40">
                <td className="p-3">
                  <Link className="text-blue-300 hover:underline" href={`/market/${r.pair_id}`}>
                    Drill in
                  </Link>
                  <div className="text-xs text-zinc-500 mt-1 font-mono">{r.pair_id}</div>
                </td>
                <td className="p-3">
                  <div className="font-mono text-xs text-zinc-300">{r.kalshi_ticker}</div>
                  <div className="text-zinc-400 line-clamp-2">{r.title_k}</div>
                </td>
                <td className="p-3">
                  <div className="font-mono text-xs text-zinc-300">{r.poly_condition_id}</div>
                  <div className="text-zinc-400 line-clamp-2">{r.title_p}</div>
                </td>
                <td className="p-3 tabular-nums">{r.spread_pct?.toFixed(2)}</td>
                <td className="p-3 tabular-nums">{r.implied_edge?.toFixed(4)}</td>
                <td className="p-3 tabular-nums">{r.round_trip_edge?.toFixed(4)}</td>
                <td className="p-3 tabular-nums text-xs">
                  {Number(r.volume_kalshi || 0).toFixed(0)} / {Number(r.volume_poly_24h || 0).toFixed(0)}
                </td>
                <td className="p-3 text-xs text-zinc-400">{r.arb_type}</td>
              </tr>
            ))}
            {sorted.length === 0 ? (
              <tr>
                <td className="p-6 text-zinc-500" colSpan={8}>
                  No opportunities yet. Wait for ingestion cycle (check backend logs / docker compose).
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
