"use client";

import { useState, useEffect, useRef, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MessageSquare, ExternalLink, Wand2, Send, GitBranch, Brain, Image, ChevronDown, ChevronUp } from "lucide-react";
import { getBuild, resolveDeployUrl, modifyBuild } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { AgentSteps } from "@/components/AgentSteps";
import { AppPreview } from "@/components/AppPreview";
import { CodePreview } from "@/components/CodePreview";
import { cn } from "@/lib/utils";
import type { Build, ReasoningEntry } from "@/lib/types";

const ACTIVE_STATUSES = new Set(["pending", "planning", "coding", "reviewing", "deploying"]);

export default function BuildDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [build, setBuild] = useState<Build | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [tab, setTab] = useState<"preview" | "code">("preview");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Modify state
  const [modifyText, setModifyText] = useState("");
  const [modifying, setModifying] = useState(false);
  const [modifyError, setModifyError] = useState("");
  const [showReasoning, setShowReasoning] = useState(false);

  useEffect(() => {
    if (!id) return;
    let failCount = 0;

    const fetchBuild = () => {
      getBuild(id)
        .then((data) => {
          setBuild(data);
          setLoadError(false);
          failCount = 0;
        })
        .catch(() => {
          failCount++;
          if (failCount >= 3) setLoadError(true);
        });
    };

    fetchBuild();
    intervalRef.current = setInterval(fetchBuild, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [id]);

  // Stop polling when build reaches terminal state
  useEffect(() => {
    if (build && !ACTIVE_STATUSES.has(build.status) && intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [build]);

  const handleModify = async (e: FormEvent) => {
    e.preventDefault();
    if (!id || !modifyText.trim()) return;

    setModifying(true);
    setModifyError("");
    try {
      const newBuild = await modifyBuild(id, modifyText.trim());
      router.push(`/build/${newBuild.id}`);
    } catch (err) {
      setModifyError(err instanceof Error ? err.message : "Failed to modify");
    } finally {
      setModifying(false);
    }
  };

  if (!build && loadError) {
    return (
      <div className="flex min-h-[calc(100vh-48px)] items-center justify-center">
        <div className="text-center">
          <p className="font-mono text-sm text-red-400">Build not found</p>
          <Link href="/" className="mt-3 inline-block font-mono text-xs text-neutral-500 hover:text-neutral-300">
            &larr; Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!build) {
    return (
      <div className="flex min-h-[calc(100vh-48px)] items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-700 border-t-neutral-400" />
        <span className="ml-3 font-mono text-sm text-neutral-600">Loading build...</span>
      </div>
    );
  }

  // Parse raw steps (backend stores string[])
  const rawSteps: string[] = (() => {
    if (!build.steps) return [];
    try {
      return JSON.parse(build.steps);
    } catch {
      return [];
    }
  })();

  // Parse failedAt status from error field: "[coding] Error message"
  const failedAtStatus = build.error?.match(/^\[(\w+)\]/)?.[1] ?? null;

  // Parse reasoning log
  const reasoningEntries: ReasoningEntry[] = (() => {
    if (!build.reasoning_log) return [];
    try { return JSON.parse(build.reasoning_log); } catch { return []; }
  })();

  const isActive = ACTIVE_STATUSES.has(build.status);
  const deployUrl = resolveDeployUrl(build.deploy_url);
  const canModify = build.status === "deployed" && build.generated_code;
  const isScreenshot = build.build_type === "screenshot";

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      {/* Back link */}
      <Link
        href="/"
        className="mb-6 inline-flex items-center gap-1.5 font-mono text-xs text-neutral-600 transition-colors hover:text-neutral-300"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to feed
      </Link>

      {/* Header */}
      <div className="mb-6 flex flex-wrap items-start gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-neutral-100">
              {build.app_name ?? "Untitled Build"}
            </h1>
            <StatusBadge status={build.status} />
            {isScreenshot && (
              <span className="flex items-center gap-1 rounded border border-blue-800 bg-blue-950/50 px-2 py-0.5 font-mono text-[10px] text-blue-400">
                <Image className="h-3 w-3" />
                5V-Turbo
              </span>
            )}
            {isActive && (
              <span className="flex items-center gap-1.5 font-mono text-[10px] text-emerald-500">
                <span className="live-dot" />
                Live
              </span>
            )}
          </div>
          {build.app_description && (
            <p className="mt-1 text-sm text-neutral-500">{build.app_description}</p>
          )}
          <div className="mt-1 flex items-center gap-3">
            <p className="font-mono text-xs text-neutral-700">
              Build ID: {build.id.slice(0, 8)}
            </p>
            {build.parent_build_id && (
              <Link
                href={`/build/${build.parent_build_id}`}
                className="flex items-center gap-1 font-mono text-xs text-violet-400 hover:text-violet-300"
              >
                <GitBranch className="h-3 w-3" />
                View original
              </Link>
            )}
          </div>
        </div>

        {deployUrl && (
          <a
            href={deployUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 rounded border border-emerald-700 bg-emerald-900/40 px-4 py-2 font-semibold text-sm text-emerald-300 transition-colors hover:bg-emerald-900/70"
          >
            <ExternalLink className="h-4 w-4" />
            Open Live App
          </a>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Left: preview / code / modify */}
        <div className="space-y-4">
          {/* Original tweet */}
          <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
            <div className="mb-2 flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-sky-400" />
              <span className="font-mono text-xs text-neutral-600">
                {build.parent_build_id ? "Modification Request" : "Original Request"}
              </span>
              {build.twitter_username && (
                <span className="font-mono text-xs text-sky-500">@{build.twitter_username}</span>
              )}
            </div>
            <p className="text-sm text-neutral-300 leading-relaxed">
              {build.tweet_text || build.prompt || "No description"}
            </p>
          </div>

          {/* Preview / Code tabs */}
          {(deployUrl || build.generated_code) && (
            <div>
              <div className="mb-3 flex gap-1 rounded-lg border border-neutral-800 bg-neutral-900/40 p-1 w-fit">
                <button
                  onClick={() => setTab("preview")}
                  disabled={!deployUrl}
                  className={`rounded px-3 py-1.5 font-mono text-xs transition-colors ${
                    tab === "preview"
                      ? "bg-neutral-700 text-neutral-100"
                      : "text-neutral-500 hover:text-neutral-300 disabled:opacity-30 disabled:cursor-not-allowed"
                  }`}
                >
                  Live Preview
                </button>
                <button
                  onClick={() => setTab("code")}
                  disabled={!build.generated_code}
                  className={`rounded px-3 py-1.5 font-mono text-xs transition-colors ${
                    tab === "code"
                      ? "bg-neutral-700 text-neutral-100"
                      : "text-neutral-500 hover:text-neutral-300 disabled:opacity-30 disabled:cursor-not-allowed"
                  }`}
                >
                  View Code
                </button>
              </div>

              {tab === "preview" && deployUrl && (
                <AppPreview url={deployUrl} />
              )}
              {tab === "code" && build.generated_code && (
                <CodePreview code={build.generated_code} language="html" />
              )}
            </div>
          )}

          {/* Modify input — only show when build is deployed */}
          {canModify && (
            <form onSubmit={handleModify} className="rounded-lg border border-violet-900/50 bg-violet-950/20 p-4">
              <div className="mb-3 flex items-center gap-2">
                <Wand2 className="h-4 w-4 text-violet-400" />
                <span className="font-semibold text-sm text-violet-300">Modify this app</span>
                <span className="font-mono text-[10px] text-violet-600">reply to iterate</span>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={modifyText}
                  onChange={(e) => { setModifyText(e.target.value); setModifyError(""); }}
                  placeholder="Add dark mode, make buttons bigger, add a timer..."
                  disabled={modifying}
                  className={cn(
                    "flex-1 rounded border border-neutral-800 bg-neutral-950 px-3 py-2 font-mono text-sm text-neutral-200 placeholder:text-neutral-700 outline-none",
                    "focus:border-violet-700/60 focus:ring-1 focus:ring-violet-700/30",
                    modifying && "opacity-50"
                  )}
                />
                <button
                  type="submit"
                  disabled={modifying || !modifyText.trim()}
                  className="flex items-center gap-2 rounded border border-violet-700 bg-violet-900/60 px-4 py-2 font-semibold text-sm text-violet-200 transition-colors hover:bg-violet-800/60 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {modifying ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-violet-300 border-t-transparent" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                  Modify
                </button>
              </div>
              {modifyError && (
                <p className="mt-2 font-mono text-xs text-red-400">{modifyError}</p>
              )}
            </form>
          )}

          {/* Error */}
          {build.status === "failed" && build.error && (
            <div className="rounded-lg border border-red-900 bg-red-950/30 p-4">
              <p className="mb-1 font-mono text-xs uppercase tracking-wider text-red-500">
                Build Failed
              </p>
              <p className="font-mono text-sm text-red-400">
                {build.error.replace(/^\[\w+\]\s*/, "")}
              </p>
            </div>
          )}
        </div>

        {/* Right: agent steps + metadata */}
        <div className="space-y-5">
          {/* Agent steps */}
          <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-5">
            <h3 className="mb-4 font-semibold text-sm text-neutral-300">Agent Pipeline</h3>
            <AgentSteps
              buildStatus={build.status}
              failedAtStatus={failedAtStatus}
              rawSteps={rawSteps}
            />
          </div>

          {/* GLM Reasoning (thinking mode) */}
          {reasoningEntries.length > 0 && (
            <div className="rounded-lg border border-purple-900/50 bg-purple-950/20 p-5">
              <button
                onClick={() => setShowReasoning(!showReasoning)}
                className="flex w-full items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-purple-400" />
                  <h3 className="font-semibold text-sm text-purple-300">GLM Reasoning</h3>
                  <span className="font-mono text-[10px] text-purple-600">
                    {reasoningEntries.length} stage{reasoningEntries.length !== 1 ? "s" : ""}
                  </span>
                </div>
                {showReasoning ? (
                  <ChevronUp className="h-4 w-4 text-purple-500" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-purple-500" />
                )}
              </button>
              {showReasoning && (
                <div className="mt-3 space-y-3">
                  {reasoningEntries.map((entry, i) => (
                    <div key={i} className="rounded border border-purple-900/30 bg-neutral-950 p-3">
                      <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-purple-500">
                        {entry.stage}
                      </span>
                      <p className="font-mono text-xs text-neutral-400 leading-relaxed whitespace-pre-wrap">
                        {entry.reasoning}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Metadata */}
          <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-5 space-y-3">
            <h3 className="font-semibold text-sm text-neutral-300">Details</h3>
            <MetaRow label="Created" value={new Date(build.created_at).toLocaleString()} />
            {build.deployed_at && (
              <MetaRow label="Deployed" value={new Date(build.deployed_at).toLocaleString()} />
            )}
            {build.twitter_username && (
              <MetaRow label="Requested by" value={`@${build.twitter_username}`} />
            )}
            {build.parent_build_id && (
              <MetaRow label="Type" value="Modification" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 text-xs">
      <span className="font-mono text-neutral-600 shrink-0">{label}</span>
      <span className="text-neutral-400 text-right">{value}</span>
    </div>
  );
}
