"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useUser } from "@clerk/nextjs";

interface ScanResult {
  label: string;
  kalshi_price: number;
  poly_price: number;
  gap: number;
  net_profit: number;
  direction: string;
  is_opportunity: boolean;
  timestamp: string;
}

interface ScanData {
  results: ScanResult[];
  last_scan: string;
  total_pairs: number;
  opportunities_found: number;
}

const API_URL = "https://thearbi-production.up.railway.app";

function PriceBar({ value }: { value: number }) {
  const pct = Math.min(value * 100, 100);
  return (
    <div className="h-1 w-full bg-zinc-800 rounded-full overflow-hidden">
      <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
    </div>
  );
}

function PairRow({ result }: { result: ScanResult }) {
  const isOpp = result.is_opportunity;
  return (
    <div className={`rounded-lg border px-5 py-4 transition-all duration-300 ${isOpp ? "border-emerald-500/50 bg-emerald-950/30" : "border-zinc-800 bg-zinc-900/50"}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            {isOpp && (
              <span className="inline-flex items-center gap-1 text-xs font-mono font-bold text-emerald-400 bg-emerald-400/10 border border-emerald-400/30 px-2 py-0.5 rounded">
                ● OPPORTUNITY
              </span>
            )}
            <span className="text-sm font-mono text-zinc-300 truncate">{result.label}</span>
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div>
              <div className="text-xs text-zinc-500 mb-1 font-mono">KALSHI</div>
              <div className="text-lg font-mono font-bold text-white">{(result.kalshi_price * 100).toFixed(1)}¢</div>
              <PriceBar value={result.kalshi_price} />
            </div>
            <div>
              <div className="text-xs text-zinc-500 mb-1 font-mono">POLYMARKET</div>
              <div className="text-lg font-mono font-bold text-white">{(result.poly_price * 100).toFixed(1)}¢</div>
              <PriceBar value={result.poly_price} />
            </div>
          </div>
          {isOpp && (
            <div className="mt-3 text-xs font-mono text-emerald-300 bg-emerald-950/50 border border-emerald-500/20 rounded px-3 py-2">
              {result.direction}
            </div>
          )}
        </div>
        <div className="text-right shrink-0">
          <div className="text-xs text-zinc-500 font-mono mb-1">NET PROFIT</div>
          <div className={`text-2xl font-mono font-black ${isOpp ? "text-emerald-400" : "text-zinc-500"}`}>
            {(result.net_profit * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-zinc-600 font-mono mt-1">gap {(result.gap * 100).toFixed(1)}%</div>
        </div>
      </div>
    </div>
  );
}

function DashboardContent() {
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [data, setData] = useState<ScanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subscribed, setSubscribed] = useState(false);

  useEffect(() => {
    if (!isLoaded) return;
    const justSubscribed = searchParams.get("subscribed") === "true";
    if (justSubscribed) {
      setSubscribed(true);
      user?.update({ unsafeMetadata: { ...user.unsafeMetadata, subscribed: true } });
      return;
    }
    const hasSub = user?.unsafeMetadata?.subscribed === true;
    if (!hasSub) {
      router.push("/subscribe");
      return;
    }
    setSubscribed(true);
  }, [isLoaded, user, searchParams, router]);

  async function fetchData() {
    try {
      const resp = await fetch(`${API_URL}/scan`);
      if (!resp.ok) throw new Error(`API error: ${resp.status}`);
      const json = await resp.json();
      setData(json);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!subscribed) return;
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [subscribed]);

  const opportunities = data?.results.filter((r) => r.is_opportunity) ?? [];
  const monitoring = data?.results.filter((r) => !r.is_opportunity) ?? [];

  if (!subscribed) return null;

  return (
    <div className="min-h-screen bg-zinc-950 text-white font-mono">
      <div className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <div className="text-xs text-zinc-500 tracking-widest uppercase mb-0.5">Prediction Market Arbitrage</div>
            <h1 className="text-2xl font-black tracking-tight text-white">The Arbi</h1>
          </div>
          <div className="flex items-center gap-4">
            {data && (
              <>
                <div className="text-center">
                  <div className="text-xs text-zinc-500 uppercase tracking-wider">Pairs</div>
                  <div className="text-xl font-black text-white">{data.total_pairs}</div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-zinc-500 uppercase tracking-wider">Opportunities</div>
                  <div className={`text-xl font-black ${data.opportunities_found > 0 ? "text-emerald-400" : "text-zinc-500"}`}>
                    {data.opportunities_found}
                  </div>
                </div>
              </>
            )}
            <button
              onClick={() => router.push('/settings')}
              className="text-xs text-zinc-400 hover:text-white border border-zinc-700 hover:border-zinc-500 px-3 py-1.5 rounded transition-colors"
            >
              ⚙ Settings
            </button>
            <button
              onClick={fetchData}
              className="text-xs text-zinc-400 hover:text-white border border-zinc-700 hover:border-zinc-500 px-3 py-1.5 rounded transition-colors"
            >
              ↻ Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center gap-3 mb-8 text-xs font-mono">
          <div className={`w-2 h-2 rounded-full ${error ? "bg-red-500" : loading ? "bg-yellow-500 animate-pulse" : "bg-emerald-500"}`} />
          <span className="text-zinc-400">
            {error ? `Error: ${error}` : loading ? "Scanning..." : `Last scan: ${data?.last_scan ?? "—"} · Auto-refresh every 30s`}
          </span>
        </div>

        {error && (
          <div className="border border-red-500/30 bg-red-950/20 rounded-lg p-6 mb-8">
            <div className="text-red-400 font-mono text-sm mb-2">⚠ Cannot connect to scanner API</div>
            <div className="text-zinc-500 text-xs">Backend may be starting up — try refreshing in 30 seconds.</div>
          </div>
        )}

        {opportunities.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="text-xs font-mono font-bold text-emerald-400 tracking-widest uppercase">● Live Opportunities</div>
              <div className="flex-1 h-px bg-emerald-500/20" />
            </div>
            <div className="space-y-3">
              {opportunities.map((r, i) => <PairRow key={i} result={r} />)}
            </div>
          </div>
        )}

        {monitoring.length > 0 && (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="text-xs font-mono font-bold text-zinc-500 tracking-widest uppercase">Monitoring</div>
              <div className="flex-1 h-px bg-zinc-800" />
            </div>
            <div className="space-y-3">
              {monitoring.map((r, i) => <PairRow key={i} result={r} />)}
            </div>
          </div>
        )}

        {!loading && !error && data?.results.length === 0 && (
          <div className="text-center py-20 text-zinc-600 font-mono">No pairs found.</div>
        )}

        <div className="mt-16 pt-6 border-t border-zinc-800 text-center">
          <div className="text-xs text-zinc-600 font-mono">
            thearbi.com · Prediction Market Arbitrage Scanner · {user?.emailAddresses?.[0]?.emailAddress}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-zinc-950" />}>
      <DashboardContent />
    </Suspense>
  );
}
