"use client";

import { useUser, useClerk } from "@clerk/nextjs";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const { user, isLoaded } = useUser();
  const { signOut } = useClerk();
  const router = useRouter();
  const [pushoverKey, setPushoverKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    const existing = user?.unsafeMetadata?.pushover_key as string;
    if (existing) setPushoverKey(existing);
  }, [isLoaded, user]);

  async function handleSave() {
    setSaving(true);
    try {
      await user?.update({
        unsafeMetadata: {
          ...user.unsafeMetadata,
          pushover_key: pushoverKey,
        },
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    if (!pushoverKey) return;
    setTesting(true);
    setTestResult(null);
    try {
      const resp = await fetch("https://api.pushover.net/1/messages.json", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          token: "atqoz4fivmk7bi6r47fkf3wxdjnscj",
          user: pushoverKey,
          title: "The Arbi — Test Notification",
          message: "Your Pushover notifications are working! You'll receive alerts when arbitrage opportunities are found.",
          sound: "cashregister",
        }),
      });
      const data = await resp.json();
      if (data.status === 1) {
        setTestResult("success");
      } else {
        setTestResult("error");
      }
    } catch {
      setTestResult("error");
    } finally {
      setTesting(false);
    }
  }

  async function handleSignOut() {
    await signOut();
    router.push("/");
  }

  if (!isLoaded) return null;

  return (
    <div className="min-h-screen bg-zinc-950 text-white font-mono">
      {/* Header */}
      <div className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <div className="text-xs text-zinc-500 tracking-widest uppercase mb-0.5">Prediction Market Arbitrage</div>
            <h1 className="text-2xl font-black tracking-tight text-white cursor-pointer" onClick={() => router.push('/dashboard')}>The Arbi</h1>
          </div>
          <button onClick={() => router.push('/dashboard')} className="text-xs text-zinc-400 hover:text-white border border-zinc-700 px-3 py-1.5 rounded transition-colors">
            ← Dashboard
          </button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-12">
        <h2 className="text-xl font-black mb-2">Settings</h2>
        <p className="text-zinc-500 text-sm mb-10">Configure your notification preferences.</p>

        {/* Pushover section */}
        <div className="border border-zinc-800 rounded-xl p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="font-bold text-white mb-1">Phone Notifications</div>
              <div className="text-sm text-zinc-500">Get instant alerts on your phone when an arbitrage opportunity is found.</div>
            </div>
            <div className="text-xs text-zinc-600 bg-zinc-800 px-2 py-1 rounded">via Pushover</div>
          </div>

          <div className="bg-zinc-900 rounded-lg p-4 mb-4 text-sm text-zinc-400">
            <div className="font-bold text-zinc-300 mb-2">Setup instructions:</div>
            <ol className="space-y-1 list-decimal list-inside">
              <li>Download the <span className="text-white">Pushover</span> app on your phone (iOS or Android)</li>
              <li>Create a free account at <span className="text-white">pushover.net</span> — one-time $5 purchase</li>
              <li>Copy your <span className="text-white">User Key</span> from the dashboard</li>
              <li>Paste it below and click Save</li>
            </ol>
          </div>

          <label className="block text-xs text-zinc-500 mb-2">PUSHOVER USER KEY</label>
          <input
            type="text"
            value={pushoverKey}
            onChange={(e) => setPushoverKey(e.target.value)}
            placeholder="uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-sm text-white font-mono placeholder-zinc-600 focus:outline-none focus:border-zinc-500 mb-4"
          />

          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving || !pushoverKey}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-bold rounded-lg transition-colors"
            >
              {saving ? "Saving..." : saved ? "✓ Saved!" : "Save"}
            </button>
            <button
              onClick={handleTest}
              disabled={testing || !pushoverKey}
              className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-sm rounded-lg transition-colors border border-zinc-700"
            >
              {testing ? "Sending..." : "Send test notification"}
            </button>
          </div>

          {testResult === "success" && (
            <div className="mt-3 text-sm text-emerald-400">✓ Test notification sent! Check your phone.</div>
          )}
          {testResult === "error" && (
            <div className="mt-3 text-sm text-red-400">✗ Failed — double check your User Key and try again.</div>
          )}
        </div>

        {/* Account info */}
        <div className="border border-zinc-800 rounded-xl p-6 mb-6">
          <div className="font-bold text-white mb-4">Account</div>
          <div className="text-sm text-zinc-500 mb-1">Email</div>
          <div className="text-sm text-white mb-4">{user?.emailAddresses?.[0]?.emailAddress}</div>
          <div className="text-sm text-zinc-500 mb-1">Subscription</div>
          <div className="text-sm text-emerald-400 mb-6">
            {user?.unsafeMetadata?.subscribed ? "✓ Active — Information Plan ($20/month)" : "No active subscription"}
          </div>
          <button
            onClick={handleSignOut}
            className="px-4 py-2 bg-zinc-800 hover:bg-red-950 hover:border-red-800 text-zinc-400 hover:text-red-400 text-sm rounded-lg transition-colors border border-zinc-700"
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
