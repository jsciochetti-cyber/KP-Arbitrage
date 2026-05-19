"use client";

import { useCallback, useEffect, useState } from "react";

import { apiGet, parseApiError } from "@/lib/api";

type VolumeResp = {
  updated_at?: string | null;
  totals: {
    kalshi_volume_sum?: number;
    polymarket_24h_volume_sum: number;
    ratio_kalshi_to_poly: number | null;
    kalshi_open_interest_volume_sum?: number;
  };
  top_kalshi: { ticker?: string; title?: string; volume?: number }[];
  top_polymarket: { condition_id?: string; question?: string; volume_24h?: number }[];
};

function agoLabel(iso: string | null | undefined, clientNow: Date): string {
  if (!iso) return "unknown";
  const then = new Date(iso).getTime();
  const sec = Math.round((then - clientNow.getTime()) / 1000);
  const abs = Math.abs(sec);
  if (abs < 60) return `${abs}s ago`;
  if (abs < 3600) return `${Math.round(abs / 60)}m ago`;
  return `${Math.round(abs / 3600)}h ago`;
}

export default function VolumePage() {
  const [data, setData] = useState<VolumeResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);

  const run = useCallback(async () => {
    try {
      setData(await apiGet<VolumeResp>("/v1/volume"));
      setFetchedAt(new Date());
      setErr(null);
    } catch (e) {
      setErr(parseApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    run();
    const id = window.setInterval(run, 15000);
    return () => window.clearInterval(id);
  }, [run]);

  const kVol = data?.totals.kalshi_volume_sum ?? data?.totals.kalshi_open_interest_volume_sum ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Volume dashboard</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Aggregates from cached ingestion snapshots. Ratio is Kalshi contracts / Polymarket USD — directional only.
          </p>
          {fetchedAt ? (
            <p className="text-xs text-zinc-500 mt-1">
              Updated: {agoLabel(data?.updated_at, fetchedAt)}
              {data?.updated_at ? ` (snapshot ${new Date(data.updated_at).toLocaleString()})` : ""}
            </p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => run()}
          className="text-sm rounded-lg border border-zinc-700 px-3 py-2 hover:bg-zinc-900"
        >
          Refresh
        </button>
      </div>
      {err ? <div className="text-sm text-red-400">{err}</div> : null}
      {loading && !data ? (
        <div className="animate-pulse rounded-xl border border-zinc-800 h-32 bg-zinc-900/50" />
      ) : null}
      {data ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-xl border border-zinc-800 p-4">
            <div className="text-sm text-zinc-400">Kalshi volume (contracts, cached universe)</div>
            <div className="mt-2 text-2xl tabular-nums">{kVol.toFixed(0)}</div>
          </div>
          <div className="rounded-xl border border-zinc-800 p-4">
            <div className="text-sm text-zinc-400">Polymarket 24h volume (USD, cached universe)</div>
            <div className="mt-2 text-2xl tabular-nums">{data.totals.polymarket_24h_volume_sum.toFixed(0)}</div>
          </div>
          <div className="rounded-xl border border-zinc-800 p-4">
            <div className="text-sm text-zinc-400">Ratio (K contracts / P USD)</div>
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
                <div className="mt-2 text-xs text-zinc-500 tabular-nums">vol {Number(x.volume || 0).toFixed(0)} contracts</div>
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
                <div className="mt-2 text-xs text-zinc-500 tabular-nums">24h {Number(x.volume_24h || 0).toFixed(0)} USD</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
