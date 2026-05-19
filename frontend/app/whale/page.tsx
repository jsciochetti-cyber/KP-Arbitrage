"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { apiGet, parseApiError } from "@/lib/api";

const PAGE_SIZE = 50;

type Whale = {
  id: string;
  venue: string;
  market_ref: string;
  market_title?: string;
  side: string;
  size_usd: number;
  price: number | null;
  recorded_at: string;
};

function relTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diffSec = Math.round((then - Date.now()) / 1000);
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  const abs = Math.abs(diffSec);
  if (abs < 60) return rtf.format(diffSec, "second");
  if (abs < 3600) return rtf.format(Math.round(diffSec / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diffSec / 3600), "hour");
  return rtf.format(Math.round(diffSec / 86400), "day");
}

export default function WhalePage() {
  const [rows, setRows] = useState<Whale[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [minUsd, setMinUsd] = useState(500);
  const [page, setPage] = useState(0);

  const fetchWhales = useCallback(async () => {
    try {
      const data = await apiGet<Whale[]>(`/v1/whales?min_usd=${minUsd}&limit=200`);
      setRows(data);
      setErr(null);
      setPage(0);
    } catch (e) {
      setErr(parseApiError(e));
    } finally {
      setLoading(false);
    }
  }, [minUsd]);

  useEffect(() => {
    fetchWhales();
    const id = window.setInterval(fetchWhales, 15000);
    return () => window.clearInterval(id);
  }, [fetchWhales]);

  const pageRows = useMemo(
    () => rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE),
    [rows, page],
  );
  const maxPage = Math.max(0, Math.ceil(rows.length / PAGE_SIZE) - 1);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Whale trades</h1>
          <p className="text-sm text-zinc-400 mt-1">Kalshi tape + Polymarket prints over your USD threshold.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-zinc-400">Min USD</label>
          <input
            type="number"
            min={1}
            value={minUsd}
            onChange={(e) => setMinUsd(Number(e.target.value) || 500)}
            className="w-24 rounded-lg bg-zinc-950 border border-zinc-800 px-2 py-1 text-sm"
          />
          <button
            type="button"
            onClick={() => fetchWhales()}
            className="text-sm rounded-lg border border-zinc-700 px-3 py-1 hover:bg-zinc-900"
          >
            Apply
          </button>
        </div>
      </div>

      {err ? <div className="text-sm text-red-400">{err}</div> : null}
      {loading && rows.length === 0 ? (
        <div className="animate-pulse rounded-xl border border-zinc-800 h-48 bg-zinc-900/50" />
      ) : null}

      <div className="flex items-center justify-between text-sm text-zinc-400">
        <span>
          {rows.length} trades · page {page + 1} / {maxPage + 1}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page <= 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            className="rounded border border-zinc-700 px-2 py-1 disabled:opacity-40"
          >
            Prev
          </button>
          <button
            type="button"
            disabled={page >= maxPage}
            onClick={() => setPage((p) => Math.min(maxPage, p + 1))}
            className="rounded border border-zinc-700 px-2 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
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
            {pageRows.map((w) => (
              <tr key={w.id} className="border-b border-zinc-900">
                <td className="p-3 text-xs text-zinc-400" title={w.recorded_at}>
                  {relTime(w.recorded_at)}
                </td>
                <td className="p-3 text-xs">{w.venue}</td>
                <td className="p-3 text-xs max-w-[280px]">
                  <div className="line-clamp-2">{w.market_title || w.market_ref}</div>
                  <div className="font-mono text-zinc-500 truncate">{w.market_ref}</div>
                </td>
                <td className="p-3 text-xs">{w.side || "—"}</td>
                <td className="p-3 tabular-nums">{w.size_usd.toFixed(2)}</td>
                <td className="p-3 tabular-nums">{w.price == null ? "—" : w.price.toFixed(4)}</td>
              </tr>
            ))}
            {!loading && rows.length === 0 ? (
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
