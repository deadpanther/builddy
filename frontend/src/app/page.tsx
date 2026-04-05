"use client";

import { useState } from "react";
import { Zap } from "lucide-react";
import { BuildFeed } from "@/components/BuildFeed";
import { SubmitBuild } from "@/components/SubmitBuild";

export default function DashboardPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  return (
    <div className="min-h-[calc(100vh-48px)]">
      {/* Hero header */}
      <header className="border-b border-neutral-800 bg-neutral-900/30 px-4 py-8">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-violet-400" />
              <h1 className="text-2xl font-bold text-neutral-100 tracking-tight">Builddy</h1>
            </div>
            <p className="text-sm text-neutral-500">
              Describe an app or upload a screenshot — GLM 5.1 plans, codes, reviews, and deploys it in minutes.
              Powered by thinking mode, GLM-5V-Turbo vision, CogView-4, and web search.
            </p>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          {/* Left: Live feed */}
          <BuildFeed refreshTrigger={refreshTrigger} />

          {/* Right: Submit + info */}
          <div className="space-y-5">
            <SubmitBuild onBuildCreated={() => setRefreshTrigger((n) => n + 1)} />

            {/* How it works */}
            <div className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-5">
              <h3 className="mb-3 font-semibold text-sm text-neutral-300">How it works</h3>
              <ol className="space-y-2.5">
                {[
                  { step: "1", text: "Describe your app or upload a screenshot" },
                  { step: "2", text: "GLM 5.1 researches and plans with thinking mode" },
                  { step: "3", text: "Code is generated, self-reviewed, and thumbnail created" },
                  { step: "4", text: "App deploys live — then iterate with modifications" },
                ].map(({ step, text }) => (
                  <li key={step} className="flex items-start gap-3 text-xs text-neutral-500">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-neutral-700 font-mono text-[10px] text-neutral-600">
                      {step}
                    </span>
                    {text}
                  </li>
                ))}
              </ol>
            </div>

            {/* Stats placeholder */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Builds", value: "—" },
                { label: "Deployed", value: "—" },
                { label: "Avg time", value: "—" },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-3 text-center"
                >
                  <div className="font-mono text-lg font-bold text-neutral-200">{value}</div>
                  <div className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-neutral-600">
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
