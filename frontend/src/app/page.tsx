"use client";

import { useState } from "react";
import { Sparkles, Code2, Rocket } from "lucide-react";
import { BuildFeed } from "@/components/BuildFeed";
import { SubmitBuild } from "@/components/SubmitBuild";

export default function DashboardPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  return (
    <div className="min-h-[calc(100vh-56px)]">
      {/* Hero — bold tagline, not a logo repeat */}
      <header className="relative border-b overflow-hidden" style={{ borderColor: 'var(--card-border)' }}>
        <div className="absolute inset-0 bg-grid opacity-30" />
        <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse at top, var(--accent-soft) 0%, transparent 50%)' }} />

        <div className="relative mx-auto max-w-7xl px-6 pt-12 pb-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
          <div>
            <h1 className="font-display text-4xl sm:text-5xl font-bold tracking-tight leading-[1.1]" style={{ color: 'var(--text-primary)' }}>
              See an app you love?<br />
              <span className="text-gradient">We&apos;ll build it for you.</span>
            </h1>
            <p className="mt-3 text-base max-w-lg leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              Found a cool app on X? Reply with <span className="font-mono font-medium" style={{ color: 'var(--accent)' }}>@builddy Build me</span> and our 6 AI agents will clone it from the screenshot, deploy it live, and reply with the link.
            </p>
          </div>

          {/* Tweet to build — hero CTA */}
          <div className="shrink-0 w-full lg:w-auto lg:max-w-sm">
            <div className="bento-card p-5 relative overflow-hidden">
              <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full opacity-[0.08]" style={{ background: 'var(--accent)', filter: 'blur(28px)' }} />
              <div className="flex items-center gap-2 mb-2.5">
                <svg className="h-4 w-4" style={{ color: 'var(--text-primary)' }} viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>Tweet to build</span>
              </div>
              <div className="rounded-lg px-3 py-2.5 font-mono text-[13px] leading-relaxed" style={{ background: 'var(--surface-sunken)', color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--accent)' }}>@builddy</span>{" "}Build me a pomodoro timer with sound effects and dark mode
              </div>
              <p className="mt-2.5 text-[11px] leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>
                Mention <span className="font-mono font-medium" style={{ color: 'var(--accent)' }}>@builddy</span> on X — we build it and reply with the live link.
              </p>
              <a
                href="https://x.com/intent/tweet?text=%40builddy%20Build%20me%20"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 flex items-center justify-center gap-2 w-full rounded-xl py-2 text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-[0.98]"
                style={{ background: 'var(--accent)' }}
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                Tweet @builddy
              </a>
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
                  { icon: Code2, text: "6 AI agents plan, code, and review", color: "text-amber-600 dark:text-amber-400" },
                  { icon: Rocket, text: "Deployed live — iterate with plain English", color: "text-emerald-600 dark:text-emerald-400" },
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
                { label: "Agents", value: "6" },
                { label: "Models", value: "3" },
                { label: "Steps", value: "9" },
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
