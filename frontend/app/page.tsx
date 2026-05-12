import Link from "next/link";

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Internal arbitrage console</h1>
        <p className="mt-2 text-zinc-400 max-w-2xl">
          Live ingestion from Kalshi + Polymarket, fuzzy cross-venue matching, spread ranking, paper P&amp;L, and whale
          prints. Start the stack with <code className="text-zinc-200">docker compose up --build</code>.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Tile href="/scanner" title="Arbitrage scanner" desc="Ranked cross-venue dislocations + live WS stream." />
        <Tile href="/search" title="Cross-venue search" desc="Fuzzy match Kalshi titles vs Polymarket questions." />
        <Tile href="/paper" title="Paper trading" desc="Open/close simulated positions on matched pairs." />
        <Tile href="/whale" title="Whale feed" desc="Kalshi tape + Polymarket prints over your threshold." />
        <Tile href="/volume" title="Volume dashboard" desc="Liquidity snapshot from cached market universes." />
      </div>
    </div>
  );
}

function Tile({ href, title, desc }: { href: string; title: string; desc: string }) {
  return (
    <Link
      href={href}
      className="block rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 hover:border-zinc-600 transition"
    >
      <div className="font-medium">{title}</div>
      <div className="mt-2 text-sm text-zinc-400">{desc}</div>
    </Link>
  );
}
