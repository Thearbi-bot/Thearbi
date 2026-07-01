"use client";

import { SignIn } from '@clerk/nextjs';
import { useEffect, useRef } from 'react';

const TICKERS = [
  { label: "REP Senate 2026", val: "58¢" },
  { label: "DEM House 2026", val: "79¢" },
  { label: "WTI above $71", val: "32%" },
  { label: "Trump Impeach", val: "6¢" },
  { label: "WTI above $70", val: "55¢" },
  { label: "REP House 2026", val: "22¢" },
  { label: "WTI above $72", val: "14¢" },
  { label: "DEM Senate 2026", val: "42¢" },
  { label: "WTI above $69", val: "68¢" },
  { label: "WTI above $73", val: "7¢" },
  { label: "Kalshi 58.0¢", val: "↑" },
  { label: "Poly 55.5¢", val: "↓" },
  { label: "Net +2.5%", val: "ARB" },
  { label: "Gap: 3.50%", val: "✓" },
  { label: "Poly 19.5¢", val: "↓" },
  { label: "Kalshi 22.0¢", val: "↑" },
];

export default function SignInPage() {
  const sceneRef = useRef<HTMLDivElement>(null);

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
        if (progress >= 1) {
          el.remove();
          return;
        }
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
      <div style={{ position: 'relative', zIndex: 10 }}>
        <SignIn />
      </div>
    </div>
  );
}