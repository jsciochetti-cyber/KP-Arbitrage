"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type Whale = {
  id: string;
  venue: string;
  market_ref: string;
  side: string;
  size_usd: number;
  price: number | null;
  recorded_at: string;
};

export default function WhalePage() {
  const [rows, setRows] = useState<Whale[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const data = await apiGet<Whale[]>("/v1/whales?min_usd=500&limit=200");
        setRows(data);
        setErr(null);
      } catch (e) {
        setErr((e as Error).message);
      }
    };
    run();
    const id = window.setInterval(run, 15000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Whale trades</h1>
        <p className="text-sm text-zinc-400 mt-1">Kalshi public tape + Polymarket WS prints (USD notional ≥ 500).</p>
      </div>
      {err ? <div className="text-sm text-red-400">{err}</div> : null}
      <div className="overflow-auto rounded-xl border border-zinc-800">
        <table className="min-w-[900px] w-full text-sm">
          <thead className="text-left text-zinc-400 border-b border-zinc-800">
            <tr>
              <th className="p-3">time</th>
              <th className="p-3">venue</th>
              <th className="p-3">market</th>
              <th className="p-3">side</th>
              <th className="p-3">$</th>
              <th className="p-3">px</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((w) => (
              <tr key={w.id} className="border-b border-zinc-900">
                <td className="p-3 text-xs text-zinc-400">{w.recorded_at}</td>
                <td className="p-3 text-xs">{w.venue}</td>
                <td className="p-3 font-mono text-xs">{w.market_ref}</td>
                <td className="p-3 text-xs">{w.side}</td>
                <td className="p-3 tabular-nums">{w.size_usd.toFixed(2)}</td>
                <td className="p-3 tabular-nums">{w.price == null ? "—" : w.price.toFixed(4)}</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td className="p-6 text-zinc-500" colSpan={6}>
                  No whales yet (needs live market activity + ingestion).
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
