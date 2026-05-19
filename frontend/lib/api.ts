const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!r.ok) {
    throw new Error(`${path} failed: ${r.status}`);
  }
  return (await r.json()) as T;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method: "POST" };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  const r = await fetch(`${API}${path}`, init);
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`${path} failed: ${r.status} ${t}`);
  }
  return (await r.json()) as T;
}

export function wsUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const u = new URL(base);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  return `${u.origin.replace(/\/$/, "")}/v1/ws`;
}

/** Map fetch errors to short user-facing messages. */
export function parseApiError(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e);
  const m = msg.match(/failed:\s*(\d{3})/);
  const status = m ? Number(m[1]) : 0;
  if (status === 422) return "Invalid input — check the pair ID or parameters.";
  if (status === 400) return "Bad request — missing pair or prices.";
  if (status === 404) return "Not found.";
  if (status >= 500) return "Backend error — try again shortly.";
  if (msg.toLowerCase().includes("failed to fetch") || msg.toLowerCase().includes("network")) {
    return "Cannot reach the API — check NEXT_PUBLIC_API_URL and CORS.";
  }
  return msg;
}
