"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getAutopsy,
  getRevival,
  startRevival,
  createAutopsyStream,
  type AutopsyReport,
  type RevivalPlan,
  type RevivalFeature,
  type EvidenceEntry,
  getEvidence,
} from "@/lib/api";

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  return (
    <span
      className={`difficulty-${difficulty} rounded px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider`}
    >
      {difficulty}
    </span>
  );
}

function ImpactBadge({ impact }: { impact: string }) {
  return (
    <span
      className={`impact-${impact} rounded px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider`}
    >
      {impact}
    </span>
  );
}

function EffortBadge({ effort }: { effort: string }) {
  return (
    <span
      className={`effort-${effort} rounded px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider`}
    >
      {effort}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const cls =
    priority === "critical"
      ? "bg-terminal-red/15 text-terminal-red border border-terminal-red/30"
      : priority === "high"
        ? "bg-terminal-amber/15 text-terminal-amber border border-terminal-amber/30"
        : priority === "medium"
          ? "bg-evidence-blue/15 text-evidence-blue border border-evidence-blue/30"
          : "bg-neutral-500/15 text-neutral-400 border border-neutral-500/30";
  return (
    <span className={`${cls} rounded px-2.5 py-1 font-mono text-xs uppercase tracking-wider`}>
      {priority} priority
    </span>
  );
}

function Section({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded border border-autopsy-border bg-autopsy-surface">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-5 py-3 text-left"
      >
        <h3 className="font-typewriter text-xs uppercase tracking-[0.2em] text-neutral-500">
          {title}
        </h3>
        <span className="font-mono text-xs text-neutral-600">{open ? "[-]" : "[+]"}</span>
      </button>
      {open && <div className="border-t border-autopsy-border px-5 pb-5 pt-3">{children}</div>}
    </div>
  );
}

export default function RevivePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<AutopsyReport | null>(null);
  const [plan, setPlan] = useState<RevivalPlan | null>(null);
  const [features, setFeatures] = useState<RevivalFeature[] | null>(null);
  const [revivalStatus, setRevivalStatus] = useState<string | null>(null);
  const [liveMessages, setLiveMessages] = useState<string[]>([]);
  const [evidence, setEvidence] = useState<EvidenceEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval>>();

  // Load autopsy report and revival data
  useEffect(() => {
    if (!id) return;

    const fetchData = async () => {
      try {
        const r = await getAutopsy(id);
        setReport(r);
        setRevivalStatus(r.revival_status);

        if (r.revival_status === "complete") {
          const revival = await getRevival(id);
          setPlan(revival.revival_plan);
          setFeatures(revival.revival_features);
        }
      } catch {
        // ignore
      }

      // Fetch evidence for live log
      try {
        const ev = await getEvidence(id);
        setEvidence(ev.filter((e) => e.phase === "reviving"));
      } catch {
        // ignore
      }
    };

    fetchData();
    pollingRef.current = setInterval(fetchData, 3000);

    return () => clearInterval(pollingRef.current);
  }, [id]);

  // Stop polling when revival is complete or failed
  useEffect(() => {
    if (revivalStatus === "complete" || revivalStatus === "failed") {
      clearInterval(pollingRef.current);
    }
  }, [revivalStatus]);

  // WebSocket for live updates
  useEffect(() => {
    if (!id) return;

    let ws: WebSocket;
    try {
      ws = createAutopsyStream(id);

      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.phase === "reviving" && data.message) {
            setLiveMessages((prev) => [...prev, data.message]);
          }
          if (data.phase === "revival_complete") {
            setRevivalStatus("complete");
            setPlan(data.revival_plan);
            setFeatures(data.revival_features);
          }
        } catch {
          // ignore
        }
      };
    } catch {
      // WebSocket not available
    }

    return () => { ws?.close(); };
  }, [id]);

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [liveMessages, evidence]);

  if (!report) {
    return (
      <div className="flex min-h-[calc(100vh-48px)] items-center justify-center">
        <div className="text-center">
          <div className="mb-3 inline-block h-6 w-6 animate-spin rounded-full border-2 border-terminal-green border-t-transparent" />
          <div className="font-mono text-sm text-neutral-500">Loading revival data...</div>
        </div>
      </div>
    );
  }

  const isGenerating = revivalStatus === "generating";
  const isComplete = revivalStatus === "complete" && plan;
  const isFailed = revivalStatus === "failed";
  const notStarted = !revivalStatus;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <a
          href={`/autopsy/${id}`}
          className="mb-3 inline-block font-mono text-xs text-neutral-500 transition-colors hover:text-evidence-blue"
        >
          &larr; Back to Autopsy Report
        </a>
        <div className="mb-2 flex items-center gap-3">
          {isGenerating && <span className="pulse-dot" />}
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-neutral-500">
            Case #{id}
          </span>
        </div>
        <h1 className="revival-glow font-typewriter text-3xl font-bold text-terminal-green">
          RESURRECTION PROTOCOL
        </h1>
        <p className="mt-1 font-mono text-sm text-neutral-400">{report.repo_name}</p>
      </div>

      {/* Not started — offer to start */}
      {notStarted && (
        <div className="flex flex-col items-center py-16 text-center">
          <div className="revival-heartbeat mb-6 text-6xl">&#9829;</div>
          <h2 className="mb-2 font-typewriter text-xl text-neutral-200">
            Ready to bring this repo back to life?
          </h2>
          <p className="mb-6 max-w-md text-sm text-neutral-500">
            Dr. Revive will analyze the autopsy findings and create a detailed plan to fix every issue,
            plus suggest mind-blowing features to make this project awesome again.
          </p>
          <button
            onClick={async () => {
              try {
                await startRevival(id);
                setRevivalStatus("generating");
              } catch {
                // may already be started
                setRevivalStatus("generating");
              }
            }}
            className="revival-glow rounded border border-terminal-green/40 bg-terminal-green/10 px-8 py-4 font-typewriter text-sm uppercase tracking-wider text-terminal-green transition-all hover:bg-terminal-green/20 hover:shadow-[0_0_32px_rgba(0,255,65,0.15)]"
          >
            Begin Resurrection
          </button>
        </div>
      )}

      {/* Generating — live log */}
      {isGenerating && (
        <>
          <div className="mb-6 rounded border border-autopsy-border bg-autopsy-bg">
            <div className="flex items-center gap-2 border-b border-autopsy-border px-4 py-2">
              <span className="terminal-glow font-mono text-[10px] tracking-wider">REVIVAL LOG</span>
              {connected && (
                <span className="ml-auto flex items-center gap-1.5 font-mono text-[10px] text-terminal-green">
                  <span className="pulse-dot !h-[5px] !w-[5px]" /> LIVE
                </span>
              )}
            </div>
            <div ref={logRef} className="max-h-64 overflow-y-auto px-4 py-3 font-mono text-xs">
              {evidence.map((e, i) => (
                <div key={e.id || i} className="mb-1 flex gap-2 animate-evidence-in">
                  <span className="select-none text-neutral-600">{String(i + 1).padStart(3, "0")}</span>
                  <span className="text-terminal-green">[reviving]</span>
                  <span className="break-all text-neutral-400">{e.observation}</span>
                </div>
              ))}
              {liveMessages.map((msg, i) => (
                <div key={`live-${i}`} className="mb-1 flex gap-2 animate-evidence-in">
                  <span className="select-none text-neutral-600">
                    {String(evidence.length + i + 1).padStart(3, "0")}
                  </span>
                  <span className="text-terminal-green">[live]</span>
                  <span className="break-all text-neutral-400">{msg}</span>
                </div>
              ))}
              <span className="inline-block h-4 w-1.5 animate-pulse bg-terminal-green" />
            </div>
          </div>

          <div className="flex flex-col items-center py-8 text-center">
            <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-terminal-green border-t-transparent" />
            <p className="font-typewriter text-sm text-neutral-400">
              Dr. Revive is preparing the resurrection protocol...
            </p>
          </div>
        </>
      )}

      {/* Failed */}
      {isFailed && (
        <div className="flex flex-col items-center py-16 text-center">
          <div className="mb-4 rounded border border-terminal-red/30 bg-terminal-red/5 px-6 py-4">
            <div className="mb-1 font-typewriter text-xs uppercase tracking-wider text-terminal-red">
              Revival Failed
            </div>
            <p className="text-sm text-neutral-400">The resurrection attempt encountered an error.</p>
          </div>
          <button
            onClick={async () => {
              try {
                await startRevival(id);
                setRevivalStatus("generating");
                setLiveMessages([]);
              } catch {
                // ignore
              }
            }}
            className="mt-4 revival-glow rounded border border-terminal-green/40 bg-terminal-green/10 px-6 py-3 font-typewriter text-sm uppercase tracking-wider text-terminal-green transition-all hover:bg-terminal-green/20"
          >
            Retry Revival
          </button>
        </div>
      )}

      {/* Complete — Full Revival Plan */}
      {isComplete && plan && (
        <div className="stagger-children space-y-5">
          {/* Priority + Summary */}
          <div className="rounded border-2 border-terminal-green/30 bg-terminal-green/5 p-6">
            <div className="mb-3 flex items-center gap-3">
              <div className="font-typewriter text-[10px] uppercase tracking-[0.3em] text-terminal-green">
                Resurrection Diagnosis
              </div>
              <PriorityBadge priority={plan.priority} />
            </div>
            <p className="text-sm leading-relaxed text-neutral-200">
              {plan.executive_summary}
            </p>
          </div>

          {/* Quick Wins */}
          {plan.quick_wins && plan.quick_wins.length > 0 && (
            <Section title="Quick Wins (Do These First)">
              <ul className="space-y-2">
                {plan.quick_wins.map((win, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded bg-terminal-green/15 font-mono text-[10px] text-terminal-green">
                      {i + 1}
                    </span>
                    <span className="text-sm text-neutral-300">{win}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {/* Phased Revival Plan */}
          {plan.phases && plan.phases.length > 0 && (
            <div className="space-y-4">
              <h2 className="font-typewriter text-xs uppercase tracking-[0.2em] text-neutral-500">
                Phased Revival Plan
              </h2>
              {plan.phases.map((phase) => (
                <div
                  key={phase.phase_number}
                  className="rounded border border-autopsy-border bg-autopsy-surface"
                >
                  <div className="flex items-center justify-between border-b border-autopsy-border px-5 py-3">
                    <div className="flex items-center gap-3">
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-terminal-green/15 font-mono text-sm font-bold text-terminal-green">
                        {phase.phase_number}
                      </span>
                      <div>
                        <h3 className="font-typewriter text-sm font-bold text-neutral-200">
                          {phase.title}
                        </h3>
                        <p className="font-mono text-[10px] text-neutral-500">
                          Est. {phase.estimated_effort}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="px-5 py-3">
                    <p className="mb-3 text-sm text-neutral-400">{phase.description}</p>
                    <div className="space-y-2">
                      {phase.actions.map((action, i) => (
                        <div
                          key={i}
                          className="rounded border border-autopsy-border-light bg-autopsy-bg px-4 py-3"
                        >
                          <div className="mb-1 flex items-center gap-2">
                            <DifficultyBadge difficulty={action.difficulty} />
                            <span className="font-mono text-xs text-evidence-blue">
                              {action.target}
                            </span>
                          </div>
                          <p className="text-sm text-neutral-200">{action.action}</p>
                          <p className="mt-1 text-xs italic text-neutral-500">
                            {action.rationale}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Specialized Sections */}
          {plan.architecture_recommendations && (
            <Section title="Architecture Recommendations" defaultOpen={false}>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-neutral-300">
                {plan.architecture_recommendations}
              </p>
            </Section>
          )}

          {plan.testing_strategy && (
            <Section title="Testing Strategy" defaultOpen={false}>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-neutral-300">
                {plan.testing_strategy}
              </p>
            </Section>
          )}

          {plan.dependency_overhaul && (
            <Section title="Dependency Overhaul" defaultOpen={false}>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-neutral-300">
                {plan.dependency_overhaul}
              </p>
            </Section>
          )}

          {plan.security_fixes && plan.security_fixes.length > 0 && (
            <Section title="Security Fixes" defaultOpen={false}>
              <ul className="space-y-2">
                {plan.security_fixes.map((fix, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded bg-terminal-red/15 font-mono text-[10px] text-terminal-red">
                      !
                    </span>
                    <span className="text-sm text-neutral-300">{fix}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {plan.tech_debt_payoff_order && plan.tech_debt_payoff_order.length > 0 && (
            <Section title="Tech Debt Payoff Order" defaultOpen={false}>
              <ol className="space-y-2">
                {plan.tech_debt_payoff_order.map((debt, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-neutral-300">
                    <span className="mt-1 font-mono text-xs text-terminal-amber">
                      {String(i + 1).padStart(2, "0")}.
                    </span>
                    <span>{debt}</span>
                  </li>
                ))}
              </ol>
            </Section>
          )}

          {plan.community_revival_plan && (
            <Section title="Community Revival Plan" defaultOpen={false}>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-neutral-300">
                {plan.community_revival_plan}
              </p>
            </Section>
          )}

          {/* Feature Ideas */}
          {features && features.length > 0 && (
            <div>
              <h2 className="mb-4 font-typewriter text-xs uppercase tracking-[0.2em] text-neutral-500">
                Mind-Blowing Feature Ideas
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {features.map((feature, i) => (
                  <div
                    key={i}
                    className="rounded border border-autopsy-border bg-autopsy-surface p-5 transition-all hover:border-revival-purple/30"
                  >
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <h3 className="font-typewriter text-sm font-bold text-neutral-100">
                        {feature.title}
                      </h3>
                    </div>
                    <div className="mb-3 flex flex-wrap gap-1.5">
                      <ImpactBadge impact={feature.impact} />
                      <EffortBadge effort={feature.effort} />
                    </div>
                    <p className="mb-2 text-sm text-neutral-300">{feature.description}</p>
                    <div className="mb-2 rounded bg-revival-purple/5 px-3 py-2 text-xs text-revival-purple">
                      <span className="font-semibold">Why this changes everything:</span>{" "}
                      {feature.why_this_changes_everything}
                    </div>
                    <p className="font-mono text-xs text-neutral-500">
                      <span className="text-evidence-blue">How:</span> {feature.technical_approach}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-center pt-4">
            <a
              href={`/autopsy/${id}`}
              className="rounded border border-autopsy-border-light bg-autopsy-surface px-6 py-3 font-typewriter text-sm uppercase tracking-wider text-neutral-400 transition-all hover:border-terminal-green/40 hover:text-terminal-green"
            >
              &larr; Back to Autopsy Report
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
