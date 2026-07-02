"use client";

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

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
];

export default function SubscribePage() {
  const sceneRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    function spawnTicker() {
      if (!scene) return;
      const t = TICKERS[Math.floor(Math.random() * TICKERS.length)];
      const el = document.createElement('div');
      const isGreen = t.val === "↑" || t.val === "ARB" || t.val === "✓";
      el.style.cssText = `
        position: absolute;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        font-weight: 600;
        padding: 5px 10px;
        border-radius: 6px;
        white-space: nowrap;
        pointer-events: none;
        color: ${isGreen ? '#4ade80' : '#71717a'};
        border: 1px solid ${isGreen ? 'rgba(74,222,128,0.2)' : 'rgba(113,113,122,0.15)'};
        background: ${isGreen ? 'rgba(74,222,128,0.04)' : 'rgba(113,113,122,0.03)'};
        left: ${Math.random() * (scene.offsetWidth - 200)}px;
        bottom: 0px;
        opacity: 0;
        transition: none;
      `;
      el.textContent = `${t.label}  ${t.val}`;
      scene.appendChild(el);

      const dur = (8 + Math.random() * 8) * 1000;
      const start = performance.now();

      function animate(now: number) {
        const elapsed = now - start;
        const progress = elapsed / dur;
        if (progress >= 1) { el.remove(); return; }
        const y = progress * (scene!.offsetHeight + 100);
        const opacity = progress < 0.1 ? progress / 0.1 : progress > 0.85 ? (1 - progress) / 0.15 : 1;
        el.style.transform = `translateY(-${y}px)`;
        el.style.opacity = String(opacity);
        requestAnimationFrame(animate);
      }
      requestAnimationFrame(animate);
    }

    for (let i = 0; i < 8; i++) setTimeout(spawnTicker, i * 200);
    const interval = setInterval(spawnTicker, 600);
    return () => clearInterval(interval);
  }, []);

  async function handleSubscribe() {
    const res = await fetch('/api/checkout', { method: 'POST' });
    const data = await res.json();
    if (data.url) window.location.href = data.url;
  }

  return (
    <div
      ref={sceneRef}
      style={{
        minHeight: '100vh',
        background: '#09090b',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{
        position: 'relative',
        zIndex: 10,
        background: 'white',
        borderRadius: '16px',
        padding: '40px 48px',
        width: '380px',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: '13px', color: '#71717a', marginBottom: '8px', fontFamily: 'monospace' }}>
          PREDICTION MARKET ARBITRAGE
        </div>
        <h1 style={{ fontSize: '24px', fontWeight: '800', color: '#09090b', marginBottom: '8px' }}>
          The Arbi
        </h1>
        <p style={{ fontSize: '14px', color: '#52525b', marginBottom: '32px', lineHeight: '1.6' }}>
          Real-time arbitrage scanner across Kalshi and Polymarket. Find price gaps, calculate profit, and never miss an opportunity.
        </p>

        <div style={{ background: '#f4f4f5', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
          <div style={{ fontSize: '36px', fontWeight: '800', color: '#09090b' }}>$20</div>
          <div style={{ fontSize: '13px', color: '#71717a' }}>per month</div>
          <div style={{ marginTop: '16px', textAlign: 'left' }}>
            {[
              'Live price scanner every 30 seconds',
              'Election & WTI oil pairs',
              'Profit calculations after fees',
              'Phone notifications on opportunities',
              'Web dashboard access',
            ].map((f, i) => (
              <div key={i} style={{ fontSize: '13px', color: '#3f3f46', padding: '4px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#22c55e', fontWeight: '700' }}>✓</span> {f}
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={handleSubscribe}
          style={{
            width: '100%',
            padding: '14px',
            background: '#09090b',
            color: 'white',
            borderRadius: '10px',
            fontSize: '15px',
            fontWeight: '600',
            border: 'none',
            cursor: 'pointer',
            marginBottom: '12px',
          }}
        >
          Start for $20/month →
        </button>
        <div style={{ fontSize: '12px', color: '#a1a1aa' }}>
          Cancel anytime · Secured by Stripe
        </div>
      </div>
    </div>
  );
}
