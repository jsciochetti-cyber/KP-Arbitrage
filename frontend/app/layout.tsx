import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Kalshi × Polymarket Arb",
  description: "Internal arbitrage scanner + paper trading",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur sticky top-0 z-10">
            <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between gap-4">
              <Link href="/" className="font-semibold tracking-tight">
                Kalshi × Polymarket Arb
              </Link>
              <nav className="flex flex-wrap gap-3 text-sm text-zinc-300">
                <Link className="hover:text-white" href="/scanner">
                  Scanner
                </Link>
                <Link className="hover:text-white" href="/search">
                  Search
                </Link>
                <Link className="hover:text-white" href="/paper">
                  Paper
                </Link>
                <Link className="hover:text-white" href="/whale">
                  Whales
                </Link>
                <Link className="hover:text-white" href="/volume">
                  Volume
                </Link>
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
