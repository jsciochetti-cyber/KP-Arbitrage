"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type VolumeResp = {
  totals: { kalshi_open_interest_volume_sum: number; polymarket_24h_volume_sum: number; ratio_kalshi_to_poly: number | null };
  top_kalshi: { ticker?: string; title?: string; volume?: number }[];
  top_polymarket: { condition_id?: string; question?: string; volume_24h?: number }[];
};

export default function VolumePage() {
  const [data, setData] = useState<VolumeResp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        setData(await apiGet<VolumeResp>("/v1/volume"));
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
        <h1 className="text-xl font-semibold">Volume dashboard</h1>
        <p className="text-sm text-zinc-400 mt-1">Aggregates from cached ingestion snapshots (not a perfect OI match, but directionally useful).</p>
      </div>
      {err ? <div className="text-sm text-red-400">{err}</div> : null}
      {data ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-xl border border-zinc-800 p-4">
            <div className="text-sm text-zinc-400">Kalshi Σ volume (cached universe)</div>
            <div className="mt-2 text-2xl tabular-nums">{data.totals.kalshi_open_interest_volume_sum.toFixed(0)}</div>
          </div>
          <div className="rounded-xl border border-zinc-800 p-4">
            <div className="text-sm text-zinc-400">Polymarket Σ 24h volume (cached universe)</div>
            <div className="mt-2 text-2xl tabular-nums">{data.totals.polymarket_24h_volume_sum.toFixed(0)}</div>
          </div>
          <div className="rounded-xl border border-zinc-800 p-4">
            <div className="text-sm text-zinc-400">Ratio (K / P)</div>
            <div className="mt-2 text-2xl tabular-nums">{data.totals.ratio_kalshi_to_poly?.toFixed(3) ?? "—"}</div>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 text-sm text-zinc-300">Top Kalshi</div>
          <div className="divide-y divide-zinc-900">
            {(data?.top_kalshi || []).map((x) => (
              <div key={x.ticker} className="p-4">
                <div className="font-mono text-xs text-zinc-400">{x.ticker}</div>
                <div className="mt-2 text-sm">{x.title}</div>
                <div className="mt-2 text-xs text-zinc-500 tabular-nums">vol {Number(x.volume || 0).toFixed(0)}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 text-sm text-zinc-300">Top Polymarket</div>
          <div className="divide-y divide-zinc-900">
            {(data?.top_polymarket || []).map((x) => (
              <div key={x.condition_id} className="p-4">
                <div className="font-mono text-xs text-zinc-400">{x.condition_id}</div>
                <div className="mt-2 text-sm">{x.question}</div>
                <div className="mt-2 text-xs text-zinc-500 tabular-nums">24h {Number(x.volume_24h || 0).toFixed(0)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
