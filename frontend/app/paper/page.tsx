"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiGet, apiPost, parseApiError } from "@/lib/api";

type PortfolioRow = {
  id: string;
  pair_id: string;
  status: string;
  quantity: number;
  entry_value: number | null;
  mark_value: number | null;
  realized_pnl: number | null;
  opened_at: string | null;
  closed_at: string | null;
};

type PairOption = {
  id: string;
  kalshi_ticker: string;
  poly_condition_id: string;
  match_score: number;
};

export default function PaperPage() {
  const [rows, setRows] = useState<PortfolioRow[]>([]);
  const [pairs, setPairs] = useState<PairOption[]>([]);
  const [pairId, setPairId] = useState("");
  const [qty, setQty] = useState("1");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [closingAll, setClosingAll] = useState(false);

  const refresh = async () => {
    const data = await apiGet<PortfolioRow[]>("/v1/paper/portfolio");
    setRows(data);
  };

  useEffect(() => {
    (async () => {
      try {
        await refresh();
        const p = await apiGet<PairOption[]>("/v1/pairs");
        setPairs(p);
        setErr(null);
      } catch (e) {
        setErr(parseApiError(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const open = async () => {
    setErr(null);
    const n = Number(qty);
    if (!pairId.trim() || !Number.isFinite(n) || n < 1) {
      setErr("Enter a valid pair ID and quantity of at least 1.");
      return;
    }
    try {
      await apiPost("/v1/paper/orders", { pair_id: pairId.trim(), quantity: n });
      setPairId("");
      await refresh();
    } catch (e) {
      setErr(parseApiError(e));
    }
  };

  const close = async (id: string) => {
    setErr(null);
    try {
      await apiPost(`/v1/paper/orders/${id}/close`);
      await refresh();
    } catch (e) {
      setErr(parseApiError(e));
    }
  };

  const closeAll = async () => {
    const openRows = rows.filter((r) => r.status === "open");
    if (openRows.length === 0) return;
    setClosingAll(true);
    setErr(null);
    try {
      for (const r of openRows) {
        await apiPost(`/v1/paper/orders/${r.id}/close`);
      }
      await refresh();
    } catch (e) {
      setErr(parseApiError(e));
    } finally {
      setClosingAll(false);
    }
  };

  const openCount = rows.filter((r) => r.status === "open").length;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Paper trading</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Opens a simulated position on a matched pair (UUID from scanner or dropdown below).
        </p>
      </div>

      <div className="rounded-xl border border-zinc-800 p-4 space-y-3 max-w-xl">
        <div className="text-sm text-zinc-300">Open</div>
        {pairs.length > 0 ? (
          <select
            value={pairId}
            onChange={(e) => setPairId(e.target.value)}
            className="w-full rounded-lg bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm font-mono"
          >
            <option value="">Select a matched pair…</option>
            {pairs.map((p) => (
              <option key={p.id} value={p.id}>
                {p.kalshi_ticker.slice(0, 24)}… / {p.match_score.toFixed(0)}% match
              </option>
            ))}
          </select>
        ) : null}
        <input
          value={pairId}
          onChange={(e) => setPairId(e.target.value)}
          placeholder="pair_id (UUID)"
          className="w-full rounded-lg bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm outline-none focus:border-zinc-600 font-mono"
        />
        <input
          type="number"
          min={1}
          value={qty}
          onChange={(e) => setQty(e.target.value)}
          placeholder="quantity"
          className="w-full rounded-lg bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm outline-none focus:border-zinc-600"
        />
        <div className="flex gap-2">
          <button onClick={open} className="text-sm rounded-lg bg-blue-600 px-3 py-2 hover:bg-blue-500">
            Submit paper order
          </button>
          {openCount > 0 ? (
            <button
              type="button"
              disabled={closingAll}
              onClick={closeAll}
              className="text-sm rounded-lg border border-zinc-700 px-3 py-2 hover:bg-zinc-900 disabled:opacity-50"
            >
              {closingAll ? "Closing…" : `Close all (${openCount})`}
            </button>
          ) : null}
        </div>
      </div>

      {err ? <div className="text-sm text-red-400">{err}</div> : null}
      {loading ? <div className="animate-pulse rounded-xl border border-zinc-800 h-32 bg-zinc-900/50" /> : null}

      <div className="overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="text-left text-zinc-400 border-b border-zinc-800">
            <tr>
              <th className="p-3">id</th>
              <th className="p-3">pair</th>
              <th className="p-3">status</th>
              <th className="p-3">qty</th>
              <th className="p-3">entry</th>
              <th className="p-3">mark</th>
              <th className="p-3">pnl</th>
              <th className="p-3"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-zinc-900">
                <td className="p-3 font-mono text-xs">{r.id.slice(0, 8)}…</td>
                <td className="p-3 font-mono text-xs">
                  <Link href={`/market/${r.pair_id}`} className="text-blue-300 hover:underline">
                    {r.pair_id.slice(0, 8)}…
                  </Link>
                </td>
                <td className="p-3">{r.status}</td>
                <td className="p-3 tabular-nums">{r.quantity}</td>
                <td className="p-3 tabular-nums">{r.entry_value?.toFixed(4) ?? "—"}</td>
                <td className="p-3 tabular-nums">{r.mark_value?.toFixed(4) ?? "—"}</td>
                <td className="p-3 tabular-nums">{r.realized_pnl?.toFixed(4) ?? "—"}</td>
                <td className="p-3">
                  {r.status === "open" ? (
                    <button
                      type="button"
                      className="text-xs rounded-lg border border-zinc-700 px-2 py-1 hover:bg-zinc-900"
                      onClick={() => close(r.id)}
                    >
                      Close
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
            {!loading && rows.length === 0 ? (
              <tr>
                <td className="p-6 text-zinc-500" colSpan={8}>
                  No paper trades yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
