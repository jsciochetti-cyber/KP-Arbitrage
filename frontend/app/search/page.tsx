"use client";

import { useEffect, useMemo, useState } from "react";

import { apiGet, parseApiError } from "@/lib/api";

type SearchResp = {
  query: string;
  kalshi: { ticker: string; title: string; score: number; yes_bid: number | null; yes_ask: number | null }[];
  polymarket: { condition_id: string; question: string; slug: string; score: number }[];
};

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [data, setData] = useState<SearchResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const canSearch = useMemo(() => q.trim().length >= 2, [q]);

  useEffect(() => {
    if (!canSearch) {
      setData(null);
      return;
    }
    setLoading(true);
    const t = window.setTimeout(async () => {
      try {
        const r = await apiGet<SearchResp>(`/v1/search?q=${encodeURIComponent(q.trim())}`);
        setData(r);
        setErr(null);
      } catch (e) {
        setErr(parseApiError(e));
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => window.clearTimeout(t);
  }, [q, canSearch]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Cross-venue search</h1>
        <p className="text-sm text-zinc-400 mt-1">Fuzzy match Kalshi titles vs Polymarket questions (REST).</p>
      </div>

      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="w-full max-w-xl rounded-lg bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm outline-none focus:border-zinc-600"
        placeholder="Type at least 2 characters…"
      />

      {loading ? <div className="text-sm text-zinc-500">Searching…</div> : null}
      {err ? <div className="text-sm text-red-400">{err}</div> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 text-sm text-zinc-300">Kalshi</div>
          <div className="divide-y divide-zinc-900">
            {(data?.kalshi || []).map((x) => (
              <div key={x.ticker} className="p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-mono text-xs text-zinc-400">{x.ticker}</div>
                  <div className="text-xs text-zinc-500">{x.score.toFixed(0)}</div>
                </div>
                <div className="mt-2 text-sm">{x.title}</div>
                <div className="mt-2 text-xs text-zinc-500 tabular-nums">
                  bid {x.yes_bid?.toFixed(3) ?? "—"} / ask {x.yes_ask?.toFixed(3) ?? "—"}
                </div>
              </div>
            ))}
            {canSearch && !loading && (data?.kalshi?.length ?? 0) === 0 ? (
              <div className="p-4 text-sm text-zinc-500">No Kalshi matches above threshold.</div>
            ) : null}
          </div>
        </div>

        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 text-sm text-zinc-300">Polymarket</div>
          <div className="divide-y divide-zinc-900">
            {(data?.polymarket || []).map((x) => (
              <div key={x.condition_id} className="p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-mono text-xs text-zinc-400">{x.slug || x.condition_id}</div>
                  <div className="text-xs text-zinc-500">{x.score.toFixed(0)}</div>
                </div>
                <div className="mt-2 text-sm">{x.question}</div>
              </div>
            ))}
            {canSearch && !loading && (data?.polymarket?.length ?? 0) === 0 ? (
              <div className="p-4 text-sm text-zinc-500">No Polymarket matches above threshold.</div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
