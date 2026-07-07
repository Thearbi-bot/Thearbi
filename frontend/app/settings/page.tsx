"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@clerk/nextjs";

const TICKERS = [
  { label: "REP Senate 2026", val: "58¢" },
  { label: "DEM House 2026", val: "79¢" },
  { label: "WTI above $71", val: "32%" },
  { label: "Trump Impeach", val: "6¢" },
  { label: "WTI above $70", val: "55¢" },
  { label: "REP House 2026", val: "22¢" },
  { label: "WTI above $72", val: "14¢" },
  { label: "DEM Senate 2026", val: "42¢" },
  { label: "Net +2.5%", val: "ARB" },
  { label: "Gap: 3.50%", val: "✓" },
  { label: "Kalshi 58.0¢", val: "↑" },
  { label: "Poly 55.5¢", val: "↓" },
];

const DEMO_PAIRS = [
  { label: "Republican Senate Control 2026", kalshi: 59.0, poly: 55.5, gap: 3.5, net: 0.5, opp: false, direction: "BUY YES on Polymarket / BUY NO on Kalshi" },
  { label: "WTI above $71 on 2026-06-30", kalshi: 27.0, poly: 31.0, gap: 4.0, net: 1.0, opp: false, direction: "BUY YES on Kalshi / BUY NO on Polymarket" },
  { label: "WTI above $72 on 2026-06-30", kalshi: 17.0, poly: 30.5, gap: 13.5, net: 10.5, opp: true, direction: "BUY YES on Kalshi / BUY NO on Polymarket" },
  { label: "Republican House Control 2026", kalshi: 22.0, poly: 19.5, gap: 2.5, net: -0.5, opp: false, direction: "BUY YES on Polymarket / BUY NO on Kalshi" },
  { label: "Democrat Senate Control 2026", kalshi: 42.0, poly: 42.5, gap: 0.5, net: -2.5, opp: false, direction: "BUY YES on Kalshi / BUY NO on Polymarket" },
];

const RESULTS = [
  { date: "Jun 30", pair: "WTI above $72", kalshi: "17¢", poly: "30.5¢", net: "+10.5%", result: "✓ Profitable" },
  { date: "Jun 25", pair: "WTI above $71", kalshi: "22¢", poly: "35¢", net: "+10.0%", result: "✓ Profitable" },
  { date: "Jun 25", pair: "WTI above $70", kalshi: "37¢", poly: "43.5¢", net: "+3.5%", result: "✓ Profitable" },
  { date: "Jun 24", pair: "WTI above $72", kalshi: "20¢", poly: "28.5¢", net: "+5.5%", result: "✓ Profitable" },
  { date: "Jun 23", pair: "REP Senate 2026", kalshi: "61¢", poly: "56¢", net: "+2.0%", result: "✓ Profitable" },
];

export default function LandingPage() {
  const heroRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { user, isLoaded } = useUser();
  const [activePairs, setActivePairs] = useState(DEMO_PAIRS);

  const isSubscribed = user?.unsafeMetadata?.subscribed === true;

  useEffect(() => {
    const scene = heroRef.current;
    if (!scene) return;
    function spawnTicker() {
      if (!scene) return;
      const t = TICKERS[Math.floor(Math.random() * TICKERS.length)];
      const el = document.createElement('div');
      const isGreen = ["↑", "ARB", "✓"].includes(t.val);
      el.style.cssText = `
        position:absolute;font-family:'Courier New',monospace;font-size:12px;font-weight:600;
        padding:5px 10px;border-radius:6px;white-space:nowrap;pointer-events:none;
        color:${isGreen ? '#4ade80' : '#71717a'};
        border:1px solid ${isGreen ? 'rgba(74,222,128,0.2)' : 'rgba(113,113,122,0.15)'};
        background:${isGreen ? 'rgba(74,222,128,0.04)' : 'rgba(113,113,122,0.03)'};
        left:${Math.random() * (scene.offsetWidth - 200)}px;bottom:0;opacity:0;transition:none;
      `;
      el.textContent = `${t.label}  ${t.val}`;
      scene.appendChild(el);
      const dur = (10 + Math.random() * 8) * 1000;
      const start = performance.now();
      function animate(now: number) {
        const p = (now - start) / dur;
        if (p >= 1) { el.remove(); return; }
        el.style.transform = `translateY(-${p * (scene!.offsetHeight + 100)}px)`;
        el.style.opacity = String(p < 0.1 ? p / 0.1 : p > 0.85 ? (1 - p) / 0.15 : 1);
        requestAnimationFrame(animate);
      }
      requestAnimationFrame(animate);
    }
    for (let i = 0; i < 10; i++) setTimeout(spawnTicker, i * 300);
    const iv = setInterval(spawnTicker, 700);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    const iv = setInterval(() => {
      setActivePairs(prev => prev.map(p => ({
        ...p,
        kalshi: Math.max(1, p.kalshi + (Math.random() - 0.5) * 2),
        poly: Math.max(1, p.poly + (Math.random() - 0.5) * 2),
      })));
    }, 2000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div style={{ background: '#09090b', minHeight: '100vh', color: 'white', fontFamily: 'monospace' }}>

      {/* Nav */}
      <nav style={{ borderBottom: '1px solid #27272a', padding: '16px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'sticky', top: 0, background: 'rgba(9,9,11,0.9)', backdropFilter: 'blur(8px)', zIndex: 100 }}>
        <div style={{ fontWeight: 900, fontSize: '18px', letterSpacing: '-0.5px' }}>The Arbi</div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {isLoaded && user ? (
            <>
              <span style={{ fontSize: '13px', color: '#a1a1aa' }}>
                {user.emailAddresses?.[0]?.emailAddress}
              </span>
              <button
                onClick={() => router.push(isSubscribed ? '/dashboard' : '/subscribe')}
                style={{ padding: '8px 16px', border: 'none', borderRadius: '8px', background: '#22c55e', color: '#000', cursor: 'pointer', fontSize: '13px', fontWeight: '700' }}
              >
                {isSubscribed ? 'Dashboard →' : 'Subscribe →'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => router.push('/sign-in')}
                style={{ padding: '8px 16px', border: '1px solid #3f3f46', borderRadius: '8px', background: 'transparent', color: '#a1a1aa', cursor: 'pointer', fontSize: '13px' }}
              >
                Sign in
              </button>
              <button
                onClick={() => router.push('/sign-up')}
                style={{ padding: '8px 16px', border: 'none', borderRadius: '8px', background: '#22c55e', color: '#000', cursor: 'pointer', fontSize: '13px', fontWeight: '700' }}
              >
                Get started
              </button>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <div ref={heroRef} style={{ position: 'relative', overflow: 'hidden', minHeight: '600px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '80px 40px', textAlign: 'center' }}>
        <div style={{ position: 'relative', zIndex: 10 }}>
          <div style={{ fontSize: '12px', color: '#4ade80', letterSpacing: '3px', marginBottom: '16px', textTransform: 'uppercase' }}>● Live Scanner</div>
          <h1 style={{ fontSize: '56px', fontWeight: '900', lineHeight: 1.05, marginBottom: '20px', letterSpacing: '-2px' }}>
            Find arbitrage gaps<br />
            <span style={{ color: '#4ade80' }}>before anyone else.</span>
          </h1>
          <p style={{ fontSize: '18px', color: '#71717a', maxWidth: '520px', lineHeight: '1.6', marginBottom: '40px' }}>
            The Arbi scans Kalshi and Polymarket every 30 seconds, finds pricing discrepancies, and alerts you instantly — so you can lock in guaranteed profit.
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            {isLoaded && user ? (
              <button
                onClick={() => router.push(isSubscribed ? '/dashboard' : '/subscribe')}
                style={{ padding: '14px 32px', background: '#22c55e', color: '#000', border: 'none', borderRadius: '10px', fontSize: '15px', fontWeight: '800', cursor: 'pointer' }}
              >
                {isSubscribed ? 'Go to Dashboard →' : 'Subscribe for $20/month →'}
              </button>
            ) : (
              <button
                onClick={() => router.push('/sign-up')}
                style={{ padding: '14px 32px', background: '#22c55e', color: '#000', border: 'none', borderRadius: '10px', fontSize: '15px', fontWeight: '800', cursor: 'pointer' }}
              >
                Start for $20/month →
              </button>
            )}
            <button
              onClick={() => document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })}
              style={{ padding: '14px 32px', background: 'transparent', color: '#a1a1aa', border: '1px solid #3f3f46', borderRadius: '10px', fontSize: '15px', cursor: 'pointer' }}
            >
              See how it works
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div style={{ borderTop: '1px solid #18181b', borderBottom: '1px solid #18181b', padding: '40px', display: 'flex', justifyContent: 'center', gap: '80px' }}>
        {[["30s", "Scan interval"], ["2", "Platforms monitored"], ["$0", "Missed if you're watching"], ["15+", "Market pairs tracked"]].map(([val, label]) => (
          <div key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '32px', fontWeight: '900', color: '#4ade80' }}>{val}</div>
            <div style={{ fontSize: '12px', color: '#71717a', marginTop: '4px' }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Live demo */}
      <div id="demo" style={{ maxWidth: '900px', margin: '0 auto', padding: '80px 40px' }}>
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <div style={{ fontSize: '12px', color: '#4ade80', letterSpacing: '3px', marginBottom: '12px' }}>LIVE DEMO</div>
          <h2 style={{ fontSize: '36px', fontWeight: '900', marginBottom: '12px' }}>This is what you see</h2>
          <p style={{ color: '#71717a', fontSize: '15px' }}>Real scanner output — prices updating every 2 seconds</p>
        </div>

        <div style={{ border: '1px solid #27272a', borderRadius: '16px', overflow: 'hidden' }}>
          <div style={{ background: '#111113', borderBottom: '1px solid #27272a', padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: '900', fontSize: '16px' }}>The Arbi</div>
            <div style={{ display: 'flex', gap: '24px' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: '#71717a' }}>PAIRS</div>
                <div style={{ fontSize: '18px', fontWeight: '900' }}>15</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: '#71717a' }}>OPPORTUNITIES</div>
                <div style={{ fontSize: '18px', fontWeight: '900', color: '#4ade80' }}>1</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '24px', background: '#09090b' }}>
            <div style={{ fontSize: '11px', color: '#4ade80', letterSpacing: '2px', marginBottom: '12px' }}>● LIVE OPPORTUNITIES</div>
            {activePairs.filter(p => p.opp).map((p, i) => (
              <div key={i} style={{ border: '1px solid rgba(74,222,128,0.3)', borderRadius: '10px', padding: '16px 20px', marginBottom: '8px', background: 'rgba(74,222,128,0.04)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <span style={{ fontSize: '11px', background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80', padding: '2px 8px', borderRadius: '4px', marginRight: '8px' }}>● OPPORTUNITY</span>
                    <span style={{ fontSize: '13px', color: '#d4d4d8' }}>{p.label}</span>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '12px' }}>
                      <div>
                        <div style={{ fontSize: '10px', color: '#71717a', marginBottom: '4px' }}>KALSHI</div>
                        <div style={{ fontSize: '20px', fontWeight: '900' }}>{p.kalshi.toFixed(1)}¢</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#71717a', marginBottom: '4px' }}>POLYMARKET</div>
                        <div style={{ fontSize: '20px', fontWeight: '900' }}>{p.poly.toFixed(1)}¢</div>
                      </div>
                    </div>
                    <div style={{ marginTop: '10px', fontSize: '12px', color: '#4ade80', background: 'rgba(74,222,128,0.05)', border: '1px solid rgba(74,222,128,0.15)', borderRadius: '6px', padding: '6px 10px' }}>{p.direction}</div>
                  </div>
                  <div style={{ textAlign: 'right', marginLeft: '16px' }}>
                    <div style={{ fontSize: '10px', color: '#71717a', marginBottom: '4px' }}>NET PROFIT</div>
                    <div style={{ fontSize: '28px', fontWeight: '900', color: '#4ade80' }}>{p.net.toFixed(1)}%</div>
                    <div style={{ fontSize: '11px', color: '#52525b' }}>gap {p.gap.toFixed(1)}%</div>
                  </div>
                </div>
              </div>
            ))}

            <div style={{ fontSize: '11px', color: '#52525b', letterSpacing: '2px', margin: '16px 0 12px' }}>MONITORING</div>
            {activePairs.filter(p => !p.opp).map((p, i) => (
              <div key={i} style={{ border: '1px solid #27272a', borderRadius: '10px', padding: '14px 20px', marginBottom: '8px', background: '#111113' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '13px', color: '#a1a1aa', marginBottom: '10px' }}>{p.label}</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                      <div>
                        <div style={{ fontSize: '10px', color: '#52525b', marginBottom: '2px' }}>KALSHI</div>
                        <div style={{ fontSize: '16px', fontWeight: '700' }}>{p.kalshi.toFixed(1)}¢</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#52525b', marginBottom: '2px' }}>POLYMARKET</div>
                        <div style={{ fontSize: '16px', fontWeight: '700' }}>{p.poly.toFixed(1)}¢</div>
                      </div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', marginLeft: '16px' }}>
                    <div style={{ fontSize: '10px', color: '#52525b', marginBottom: '2px' }}>NET PROFIT</div>
                    <div style={{ fontSize: '22px', fontWeight: '900', color: '#52525b' }}>{p.net.toFixed(1)}%</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Results */}
      <div style={{ background: '#0a0a0a', borderTop: '1px solid #18181b', borderBottom: '1px solid #18181b', padding: '80px 40px' }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <div style={{ fontSize: '12px', color: '#4ade80', letterSpacing: '3px', marginBottom: '12px' }}>TRACK RECORD</div>
            <h2 style={{ fontSize: '36px', fontWeight: '900', marginBottom: '12px' }}>Recent opportunities found</h2>
            <p style={{ color: '#71717a', fontSize: '15px' }}>Real gaps identified by the scanner</p>
          </div>
          <div style={{ border: '1px solid #27272a', borderRadius: '12px', overflow: 'hidden' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr 100px 100px 100px 120px', background: '#111113', padding: '12px 20px', fontSize: '11px', color: '#71717a', letterSpacing: '1px', borderBottom: '1px solid #27272a' }}>
              <div>DATE</div><div>PAIR</div><div>KALSHI</div><div>POLYMARKET</div><div>NET</div><div>RESULT</div>
            </div>
            {RESULTS.map((r, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '80px 1fr 100px 100px 100px 120px', padding: '14px 20px', fontSize: '13px', borderBottom: i < RESULTS.length - 1 ? '1px solid #18181b' : 'none', background: i % 2 === 0 ? '#09090b' : '#0a0a0a' }}>
                <div style={{ color: '#71717a' }}>{r.date}</div>
                <div style={{ color: '#d4d4d8' }}>{r.pair}</div>
                <div style={{ color: '#a1a1aa' }}>{r.kalshi}</div>
                <div style={{ color: '#a1a1aa' }}>{r.poly}</div>
                <div style={{ color: '#4ade80', fontWeight: '700' }}>{r.net}</div>
                <div style={{ color: '#4ade80' }}>{r.result}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* How it works */}
      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '80px 40px' }}>
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <div style={{ fontSize: '12px', color: '#4ade80', letterSpacing: '3px', marginBottom: '12px' }}>HOW IT WORKS</div>
          <h2 style={{ fontSize: '36px', fontWeight: '900' }}>Simple arbitrage, automated</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '24px' }}>
          {[
            { n: "01", title: "Scanner finds a gap", desc: "The Arbi compares prices on Kalshi and Polymarket every 30 seconds for the same event." },
            { n: "02", title: "You get alerted", desc: "When a profitable gap appears, you get an instant phone notification with exactly what to buy." },
            { n: "03", title: "You place both trades", desc: "Buy YES on the cheaper platform, NO on the more expensive one. Lock in guaranteed profit." },
          ].map(({ n, title, desc }) => (
            <div key={n} style={{ border: '1px solid #27272a', borderRadius: '12px', padding: '24px', background: '#0d0d0f' }}>
              <div style={{ fontSize: '28px', fontWeight: '900', color: '#27272a', marginBottom: '12px' }}>{n}</div>
              <div style={{ fontSize: '15px', fontWeight: '700', marginBottom: '8px', color: '#e4e4e7' }}>{title}</div>
              <div style={{ fontSize: '13px', color: '#71717a', lineHeight: '1.6' }}>{desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Pricing CTA */}
      <div style={{ borderTop: '1px solid #18181b', padding: '80px 40px', textAlign: 'center' }}>
        <div style={{ fontSize: '12px', color: '#4ade80', letterSpacing: '3px', marginBottom: '16px' }}>PRICING</div>
        <h2 style={{ fontSize: '40px', fontWeight: '900', marginBottom: '12px' }}>Start finding opportunities today</h2>
        <p style={{ color: '#71717a', fontSize: '16px', marginBottom: '40px' }}>Cancel anytime. No contracts.</p>
        <div style={{ display: 'inline-block', border: '1px solid #27272a', borderRadius: '16px', padding: '40px 48px', background: '#0d0d0f', minWidth: '320px' }}>
          <div style={{ fontSize: '48px', fontWeight: '900', color: '#4ade80' }}>$20</div>
          <div style={{ fontSize: '14px', color: '#71717a', marginBottom: '24px' }}>per month</div>
          {["Live scanner every 30 seconds", "Election & WTI oil pairs", "Profit calculations after fees", "Phone notifications", "Web dashboard"].map((f, i) => (
            <div key={i} style={{ fontSize: '14px', color: '#a1a1aa', padding: '6px 0', display: 'flex', alignItems: 'center', gap: '8px', textAlign: 'left' }}>
              <span style={{ color: '#4ade80', fontWeight: '700' }}>✓</span> {f}
            </div>
          ))}
          <button
            onClick={() => router.push(user ? (isSubscribed ? '/dashboard' : '/subscribe') : '/sign-up')}
            style={{ marginTop: '24px', width: '100%', padding: '14px', background: '#22c55e', color: '#000', border: 'none', borderRadius: '10px', fontSize: '15px', fontWeight: '800', cursor: 'pointer' }}
          >
            {user ? (isSubscribed ? 'Go to Dashboard →' : 'Subscribe Now →') : 'Get started →'}
          </button>
        </div>
      </div>

      <div style={{ borderTop: '1px solid #18181b', padding: '24px 40px', textAlign: 'center', fontSize: '12px', color: '#52525b' }}>
        thearbi.com · Prediction Market Arbitrage Scanner
      </div>
    </div>
  );
}
