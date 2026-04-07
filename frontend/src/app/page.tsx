"use client";

import { useState } from "react";
import { Zap, Sparkles, Code2, Rocket } from "lucide-react";
import { BuildFeed } from "@/components/BuildFeed";
import { SubmitBuild } from "@/components/SubmitBuild";

export default function DashboardPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  return (
    <div className="min-h-[calc(100vh-56px)]">
      {/* Hero — warm bento header */}
      <header className="relative border-b overflow-hidden" style={{ borderColor: 'var(--card-border)' }}>
        <div className="absolute inset-0 bg-grid opacity-40" />
        <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse at top, var(--accent-soft) 0%, transparent 60%)' }} />

        <div className="relative mx-auto max-w-7xl px-6 py-10">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-bento bg-brand-500/10 dark:bg-brand-500/15 border border-brand-500/20">
              <Zap className="h-6 w-6 text-brand-500 dark:text-brand-400" />
            </div>
            <div>
              <h1 className="font-display text-3xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Builddy
              </h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                AI-powered app builder &middot; Powered by GLM 5.1
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Bento grid layout */}
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
          {/* Left: Live feed */}
          <BuildFeed refreshTrigger={refreshTrigger} />

          {/* Right: Submit + info bento cards */}
          <div className="space-y-6">
            <SubmitBuild onBuildCreated={() => setRefreshTrigger((n) => n + 1)} />

            {/* How it works — bento card */}
            <div className="bento-card p-6">
              <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>How it works</h3>
              <ol className="space-y-4">
                {[
                  { icon: Sparkles, text: "Describe your app or upload a screenshot", color: "text-brand-500 dark:text-brand-400" },
                  { icon: Code2, text: "GLM 5.1 plans, codes, and self-reviews", color: "text-amber-600 dark:text-amber-400" },
                  { icon: Rocket, text: "Deployed instantly — iterate with natural language", color: "text-emerald-600 dark:text-emerald-400" },
                ].map(({ icon: Icon, text, color }, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span
                      className="flex h-7 w-7 items-center justify-center rounded-xl text-[11px] font-bold shrink-0 mt-0.5"
                      style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}
                    >
                      {i + 1}
                    </span>
                    <div className="flex items-start gap-2">
                      <Icon className={`h-4 w-4 ${color} shrink-0 mt-0.5`} />
                      <span className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{text}</span>
                    </div>
                  </li>
                ))}
              </ol>
            </div>

            {/* Stats — bento grid */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Builds", value: "—" },
                { label: "Deployed", value: "—" },
                { label: "Avg time", value: "—" },
              ].map(({ label, value }) => (
                <div key={label} className="bento-card p-4 text-center">
                  <div className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{value}</div>
                  <div className="mt-1 font-mono text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
