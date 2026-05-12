"use client";

import { useEffect, useState } from "react";

import { apiGet, apiPost } from "@/lib/api";

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

export default function PaperPage() {
  const [rows, setRows] = useState<PortfolioRow[]>([]);
  const [pairId, setPairId] = useState("");
  const [qty, setQty] = useState("1");
  const [err, setErr] = useState<string | null>(null);

  const refresh = async () => {
    const data = await apiGet<PortfolioRow[]>("/v1/paper/portfolio");
    setRows(data);
  };

  useEffect(() => {
    refresh().catch((e) => setErr((e as Error).message));
  }, []);

  const open = async () => {
    setErr(null);
    try {
      await apiPost("/v1/paper/orders", { pair_id: pairId.trim(), quantity: Number(qty) });
      setPairId("");
      await refresh();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const close = async (id: string) => {
    setErr(null);
    try {
      await apiPost(`/v1/paper/orders/${id}/close`);
      await refresh();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Paper trading</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Opens a simulated position on a matched pair id (UUID from <code>/v1/pairs</code> or scanner).
        </p>
      </div>

      <div className="rounded-xl border border-zinc-800 p-4 space-y-3 max-w-xl">
        <div className="text-sm text-zinc-300">Open</div>
        <input
          value={pairId}
          onChange={(e) => setPairId(e.target.value)}
          placeholder="pair_id (UUID)"
          className="w-full rounded-lg bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm outline-none focus:border-zinc-600 font-mono"
        />
        <input
          value={qty}
          onChange={(e) => setQty(e.target.value)}
          placeholder="quantity"
          className="w-full rounded-lg bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm outline-none focus:border-zinc-600"
        />
        <button onClick={open} className="text-sm rounded-lg bg-blue-600 px-3 py-2 hover:bg-blue-500">
          Submit paper order
        </button>
      </div>

      {err ? <div className="text-sm text-red-400">{err}</div> : null}

      <div className="overflow-auto rounded-xl border border-zinc-800">
        <table className="min-w-[900px] w-full text-sm">
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
                <td className="p-3 font-mono text-xs">{r.id}</td>
                <td className="p-3 font-mono text-xs">{r.pair_id}</td>
                <td className="p-3">{r.status}</td>
                <td className="p-3 tabular-nums">{r.quantity}</td>
                <td className="p-3 tabular-nums">{r.entry_value?.toFixed(4) ?? "—"}</td>
                <td className="p-3 tabular-nums">{r.mark_value?.toFixed(4) ?? "—"}</td>
                <td className="p-3 tabular-nums">{r.realized_pnl?.toFixed(4) ?? "—"}</td>
                <td className="p-3">
                  {r.status === "open" ? (
                    <button className="text-xs rounded-lg border border-zinc-700 px-2 py-1 hover:bg-zinc-900" onClick={() => close(r.id)}>
                      Close
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
            {rows.length === 0 ? (
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
