"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import {
  getAutopsy,
  getEvidence,
  createAutopsyStream,
  type AutopsyReport,
  type EvidenceEntry,
} from "@/lib/api";

function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === "critical"
      ? "severity-critical"
      : severity === "warning"
        ? "severity-warning"
        : "severity-info";
  return (
    <span className={`${cls} rounded px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider`}>
      {severity}
    </span>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded border border-autopsy-border bg-autopsy-surface p-5">
      <h3 className="mb-3 font-typewriter text-xs uppercase tracking-[0.2em] text-neutral-500">
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function AutopsyPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<AutopsyReport | null>(null);
  const [evidence, setEvidence] = useState<EvidenceEntry[]>([]);
  const [liveMessages, setLiveMessages] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval>>();

  // Poll for report status
  useEffect(() => {
    if (!id) return;

    const fetchReport = () => {
      getAutopsy(id).then(setReport).catch(() => {});
      getEvidence(id).then(setEvidence).catch(() => {});
    };

    fetchReport();
    pollingRef.current = setInterval(fetchReport, 3000);

    return () => clearInterval(pollingRef.current);
  }, [id]);

  // Stop polling when complete
  useEffect(() => {
    if (report?.status === "complete" || report?.status === "failed") {
      clearInterval(pollingRef.current);
    }
  }, [report?.status]);

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
          if (data.message) {
            setLiveMessages((prev) => [...prev, data.message]);
          }
          if (data.phase === "complete" && data.report) {
            getAutopsy(id).then(setReport).catch(() => {});
          }
        } catch {
          // ignore parse errors
        }
      };
    } catch {
      // WebSocket not available
    }

    return () => { ws?.close(); };
  }, [id]);

  // Auto-scroll evidence log
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
          <div className="font-mono text-sm text-neutral-500">Loading case file...</div>
        </div>
      </div>
    );
  }

  const isActive = report.status === "cloning" || report.status === "analyzing" || report.status === "pending";
  const isDone = report.status === "complete";
  const isFailed = report.status === "failed";

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="mb-2 flex items-center gap-3">
          {isActive && <span className="pulse-dot" />}
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-neutral-500">
            Case #{id}
          </span>
          <span
            className={`rounded px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${
              isDone
                ? "bg-terminal-green/10 text-terminal-green border border-terminal-green/20"
                : isFailed
                  ? "bg-terminal-red/10 text-terminal-red border border-terminal-red/20"
                  : "bg-terminal-amber/10 text-terminal-amber border border-terminal-amber/20"
            }`}
          >
            {report.status}
          </span>
        </div>
        <h1 className="font-typewriter text-3xl font-bold text-neutral-100">
          {report.repo_name}
        </h1>
        <a
          href={report.repo_url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono text-sm text-evidence-blue hover:underline"
        >
          {report.repo_url}
        </a>
      </div>

      {/* Evidence Log (live) */}
      {(isActive || evidence.length > 0 || liveMessages.length > 0) && (
        <div className="mb-6 rounded border border-autopsy-border bg-autopsy-bg">
          <div className="flex items-center gap-2 border-b border-autopsy-border px-4 py-2">
            <span className="terminal-glow font-mono text-[10px] tracking-wider">EVIDENCE LOG</span>
            {connected && (
              <span className="ml-auto flex items-center gap-1.5 text-[10px] text-terminal-green font-mono">
                <span className="pulse-dot !w-[5px] !h-[5px]" /> LIVE
              </span>
            )}
          </div>
          <div ref={logRef} className="max-h-64 overflow-y-auto px-4 py-3 font-mono text-xs">
            {evidence.map((e, i) => (
              <div key={e.id || i} className="mb-1 flex gap-2 animate-evidence-in">
                <span className="text-neutral-600 select-none">{String(i + 1).padStart(3, "0")}</span>
                <span className="text-terminal-amber">[{e.phase}]</span>
                <span className="text-neutral-400 break-all">{e.observation}</span>
              </div>
            ))}
            {liveMessages.map((msg, i) => (
              <div key={`live-${i}`} className="mb-1 flex gap-2 animate-evidence-in">
                <span className="text-neutral-600 select-none">{String(evidence.length + i + 1).padStart(3, "0")}</span>
                <span className="text-terminal-green">[live]</span>
                <span className="text-neutral-400 break-all">{msg}</span>
              </div>
            ))}
            {isActive && (
              <span className="inline-block h-4 w-1.5 bg-terminal-green animate-type-cursor" />
            )}
          </div>
        </div>
      )}

      {/* Error */}
      {isFailed && report.error_message && (
        <div className="mb-6 rounded border border-terminal-red/30 bg-terminal-red/5 px-5 py-4">
          <div className="mb-1 font-typewriter text-xs uppercase tracking-wider text-terminal-red">
            Analysis Failed
          </div>
          <p className="font-mono text-sm text-neutral-400">{report.error_message}</p>
        </div>
      )}

      {/* Analyzing state */}
      {isActive && !isDone && (
        <div className="flex flex-col items-center py-12 text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-terminal-green border-t-transparent" />
          <p className="font-typewriter text-sm text-neutral-400">
            Dr. GLM 5.1 is performing the autopsy...
          </p>
          <p className="mt-1 text-xs text-neutral-600">
            This examination takes 1-3 minutes depending on repository size.
          </p>
        </div>
      )}

      {/* Report Content */}
      {isDone && (
        <div className="stagger-children space-y-5">
          {/* Cause of Death */}
          {report.cause_of_death && (
            <div className="rounded border-2 border-terminal-red/30 bg-terminal-red/5 p-6">
              <div className="mb-1 font-typewriter text-[10px] uppercase tracking-[0.3em] text-terminal-red">
                Cause of Death
              </div>
              <p className="font-typewriter text-xl leading-relaxed text-neutral-100">
                {report.cause_of_death}
              </p>
            </div>
          )}

          {/* Contributing Factors */}
          {report.contributing_factors && report.contributing_factors.length > 0 && (
            <Section title="Contributing Factors">
              <ul className="space-y-2">
                {report.contributing_factors.map((f, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="evidence-marker mt-0.5 text-[10px]">{i + 1}</span>
                    <span className="text-sm text-neutral-300">{f}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {/* Timeline of Decline */}
          {report.timeline && report.timeline.length > 0 && (
            <Section title="Timeline of Decline">
              <div className="relative ml-3 border-l border-autopsy-border-light pl-6 space-y-4">
                {report.timeline.map((evt, i) => (
                  <div key={i} className="relative">
                    <div className="absolute -left-[31px] top-1 h-3 w-3 rounded-full border-2 border-autopsy-border-light bg-autopsy-bg" />
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-neutral-500">{evt.date}</span>
                      <SeverityBadge severity={evt.severity} />
                    </div>
                    <p className="text-sm text-neutral-200">{evt.event}</p>
                    {evt.evidence && (
                      <p className="mt-1 font-mono text-xs text-neutral-500 italic">
                        Evidence: {evt.evidence}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Fatal Commits */}
          {report.fatal_commits && report.fatal_commits.length > 0 && (
            <Section title="Fatal Commits">
              <div className="space-y-3">
                {report.fatal_commits.map((c, i) => (
                  <div
                    key={i}
                    className="rounded border border-terminal-red/20 bg-terminal-red/5 px-4 py-3"
                  >
                    <div className="flex items-center gap-3 mb-1">
                      <code className="rounded bg-autopsy-bg px-2 py-0.5 font-mono text-xs text-terminal-red">
                        {c.hash?.slice(0, 8)}
                      </code>
                      <span className="font-mono text-xs text-neutral-500">{c.date}</span>
                    </div>
                    <p className="text-sm text-neutral-200">{c.message}</p>
                    <p className="mt-1 text-xs text-neutral-400 italic">{c.why_fatal}</p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Findings */}
          {report.findings && Object.keys(report.findings).length > 0 && (
            <Section title="Forensic Findings">
              <div className="space-y-4">
                {Object.entries(report.findings).map(([key, value]) => (
                  <div key={key}>
                    <h4 className="mb-1 font-mono text-xs font-semibold uppercase tracking-wider text-evidence-blue">
                      {key.replace(/_/g, " ")}
                    </h4>
                    <p className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap">
                      {typeof value === "string"
                        ? value
                        : JSON.stringify(value, null, 2)}
                    </p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Lessons Learned */}
          {report.lessons_learned && report.lessons_learned.length > 0 && (
            <Section title="Lessons Learned">
              <ul className="space-y-2">
                {report.lessons_learned.map((l, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-neutral-300">
                    <span className="mt-1 text-terminal-green font-mono text-xs">{String(i + 1).padStart(2, "0")}.</span>
                    <span>{l}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {/* Certificate Link */}
          <div className="flex justify-center pt-4">
            <a
              href={`/autopsy/${id}/certificate`}
              className="group rounded border border-autopsy-border-light bg-autopsy-surface px-6 py-3 font-typewriter text-sm uppercase tracking-wider text-neutral-400 transition-all hover:border-terminal-green/40 hover:text-terminal-green hover:shadow-[0_0_24px_rgba(0,255,65,0.08)]"
            >
              View Death Certificate &rarr;
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
