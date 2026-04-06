"use client";

import { useState, useEffect, useRef, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MessageSquare, ExternalLink, Wand2, Send, GitBranch, Brain, Image, ChevronDown, ChevronUp, Download, Layers, FolderOpen, Shuffle, X, Cloud, Rocket, Globe, Terminal, CheckCircle, AlertCircle, Loader2, RotateCcw } from "lucide-react";
import { getBuild, resolveDeployUrl, modifyBuild, remixBuild, retryBuild, getDownloadUrl, getBuildFiles, getBuildChain, cloudDeploy, getDeployStatus } from "@/lib/api";
import type { CloudDeployInstructions } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { AgentSteps } from "@/components/AgentSteps";
import { AppPreview } from "@/components/AppPreview";
import { CodePreview } from "@/components/CodePreview";
import { FileExplorer } from "@/components/FileExplorer";
import { VersionHistory } from "@/components/VersionHistory";
import { cn } from "@/lib/utils";
import type { Build, ReasoningEntry, TechStack, VersionEntry } from "@/lib/types";

const ACTIVE_STATUSES = new Set(["pending", "planning", "coding", "reviewing", "deploying"]);

export default function BuildDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [build, setBuild] = useState<Build | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [tab, setTab] = useState<"preview" | "code" | "files">("preview");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Modify state
  const [modifyText, setModifyText] = useState("");
  const [modifying, setModifying] = useState(false);
  const [modifyError, setModifyError] = useState("");
  const [showReasoning, setShowReasoning] = useState(false);

  // Remix state
  const [showRemixDropdown, setShowRemixDropdown] = useState(false);
  const [remixPrompt, setRemixPrompt] = useState("");
  const [remixing, setRemixing] = useState(false);
  const [remixError, setRemixError] = useState("");

  // File explorer state
  const [projectFiles, setProjectFiles] = useState<Record<string, string> | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [filesLoading, setFilesLoading] = useState(false);

  // Version history state
  const [versionChain, setVersionChain] = useState<VersionEntry[]>([]);

  // Cloud deploy state
  const [showDeployDropdown, setShowDeployDropdown] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [deployError, setDeployError] = useState("");
  const [deployInstructions, setDeployInstructions] = useState<CloudDeployInstructions | null>(null);

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

  // Load project files for multi-file builds
  useEffect(() => {
    if (!id || !build) return;
    const isMultiFile = build.complexity === "standard" || build.complexity === "fullstack";
    if (!isMultiFile || build.status !== "deployed") return;
    if (projectFiles) return; // already loaded

    setFilesLoading(true);
    getBuildFiles(id)
      .then((data) => {
        setProjectFiles(data.files);
        const paths = Object.keys(data.files);
        if (paths.length > 0 && !selectedFile) {
          // Auto-select first frontend HTML or README
          const autoSelect = paths.find(p => p === "frontend/index.html")
            || paths.find(p => p.endsWith(".html"))
            || paths.find(p => p === "README.md")
            || paths[0];
          setSelectedFile(autoSelect ?? null);
        }
      })
      .catch(() => { /* files endpoint may not exist for older builds */ })
      .finally(() => setFilesLoading(false));
  }, [id, build, projectFiles, selectedFile]);

  // Fetch version chain when build is deployed
  useEffect(() => {
    if (!id || !build || build.status !== "deployed") return;
    getBuildChain(id).then(setVersionChain).catch(() => {});
  }, [id, build]);

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

  const handleRemix = async (e: FormEvent) => {
    e.preventDefault();
    if (!id || !remixPrompt.trim()) return;

    setRemixing(true);
    setRemixError("");
    try {
      const newBuild = await remixBuild(id, remixPrompt.trim());
      router.push(`/build/${newBuild.id}`);
    } catch (err) {
      setRemixError(err instanceof Error ? err.message : "Failed to remix");
    } finally {
      setRemixing(false);
    }
  };

  const handleCloudDeploy = async (provider: "railway" | "render") => {
    if (!id) return;

    setDeploying(true);
    setDeployError("");
    setDeployInstructions(null);
    try {
      const updated = await cloudDeploy(id, provider);
      setBuild(updated);
      // Check if we got manual instructions
      if (updated.deploy_status === "manual" || updated.deploy_status === "ready") {
        const statusResult = await getDeployStatus(id);
        if (statusResult.instructions) {
          setDeployInstructions(statusResult.instructions);
        }
      }
    } catch (err) {
      setDeployError(err instanceof Error ? err.message : "Failed to deploy");
    } finally {
      setDeploying(false);
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
  const canModify = build.status === "deployed" && (build.generated_code || build.generated_files);
  const isScreenshot = build.build_type === "screenshot";
  const isMultiFile = build.complexity === "standard" || build.complexity === "fullstack";

  // Parse tech stack
  const techStack: TechStack | null = (() => {
    if (!build.tech_stack) return null;
    try { return JSON.parse(build.tech_stack); } catch { return null; }
  })();

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
            {isMultiFile && (
              <span className="flex items-center gap-1 rounded border border-violet-800 bg-violet-950/50 px-2 py-0.5 font-mono text-[10px] text-violet-400">
                <Layers className="h-3 w-3" />
                {build.complexity === "fullstack" ? "Full-stack" : "Standard"}
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

        <div className="flex items-center gap-2 shrink-0 relative">
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
          {build.zip_url && (
            <a
              href={getDownloadUrl(build.id)}
              className="flex items-center gap-2 rounded border border-violet-700 bg-violet-900/40 px-4 py-2 font-semibold text-sm text-violet-300 transition-colors hover:bg-violet-900/70"
            >
              <Download className="h-4 w-4" />
              Download Zip
            </a>
          )}
          {build.status === "deployed" && (
            <div className="relative">
              <button
                onClick={() => {
                  setShowDeployDropdown((prev) => !prev);
                  setDeployError("");
                }}
                className={cn(
                  "flex items-center gap-2 rounded border px-4 py-2 font-semibold text-sm transition-colors",
                  build.deploy_status === "live"
                    ? "border-emerald-700 bg-emerald-900/40 text-emerald-300 hover:bg-emerald-900/70"
                    : build.deploy_status === "deploying"
                      ? "border-amber-700 bg-amber-900/40 text-amber-300 hover:bg-amber-900/70"
                      : "border-orange-700 bg-orange-900/40 text-orange-300 hover:bg-orange-900/70"
                )}
              >
                {build.deploy_status === "deploying" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : build.deploy_status === "live" ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <Cloud className="h-4 w-4" />
                )}
                {build.deploy_status === "live"
                  ? "Deployed"
                  : build.deploy_status === "deploying"
                    ? "Deploying..."
                    : "Deploy to Cloud"}
              </button>
              {showDeployDropdown && (
                <div className="absolute right-0 top-full z-10 mt-2 w-96 rounded-lg border border-orange-900/50 bg-neutral-900 p-4 shadow-xl">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="flex items-center gap-2 font-semibold text-sm text-orange-300">
                      <Cloud className="h-3.5 w-3.5" />
                      Deploy to Cloud
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setShowDeployDropdown(false);
                        setDeployError("");
                        setDeployInstructions(null);
                      }}
                      className="text-neutral-600 hover:text-neutral-400"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  {/* External URL if already deployed */}
                  {build.deploy_external_url && (
                    <a
                      href={build.deploy_external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mb-3 flex items-center gap-2 rounded border border-emerald-800 bg-emerald-950/30 px-3 py-2 font-mono text-xs text-emerald-400 hover:bg-emerald-950/50"
                    >
                      <Globe className="h-3.5 w-3.5" />
                      {build.deploy_external_url}
                    </a>
                  )}

                  {/* Provider buttons */}
                  {!deployInstructions && (
                    <div className="space-y-2">
                      <button
                        onClick={() => handleCloudDeploy("railway")}
                        disabled={deploying}
                        className="flex w-full items-center gap-3 rounded border border-neutral-800 bg-neutral-950 px-3 py-3 text-left transition-colors hover:border-neutral-700 hover:bg-neutral-900 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <Rocket className="h-5 w-5 text-violet-400 shrink-0" />
                        <div className="min-w-0">
                          <span className="block text-sm font-medium text-neutral-200">Railway</span>
                          <span className="block font-mono text-[10px] text-neutral-600">Instant deploy with auto-scaling</span>
                        </div>
                        {deploying && <Loader2 className="h-4 w-4 animate-spin text-neutral-500 ml-auto" />}
                      </button>
                      <button
                        onClick={() => handleCloudDeploy("render")}
                        disabled={deploying}
                        className="flex w-full items-center gap-3 rounded border border-neutral-800 bg-neutral-950 px-3 py-3 text-left transition-colors hover:border-neutral-700 hover:bg-neutral-900 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <Globe className="h-5 w-5 text-teal-400 shrink-0" />
                        <div className="min-w-0">
                          <span className="block text-sm font-medium text-neutral-200">Render</span>
                          <span className="block font-mono text-[10px] text-neutral-600">Static and full-stack hosting</span>
                        </div>
                        {deploying && <Loader2 className="h-4 w-4 animate-spin text-neutral-500 ml-auto" />}
                      </button>
                    </div>
                  )}

                  {/* Manual instructions */}
                  {deployInstructions && (
                    <div className="space-y-3">
                      <p className="text-xs text-neutral-400">{deployInstructions.message}</p>
                      {deployInstructions.repo_url && (
                        <a
                          href={deployInstructions.repo_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 rounded border border-neutral-800 bg-neutral-950 px-3 py-2 font-mono text-xs text-sky-400 hover:bg-neutral-900"
                        >
                          <ExternalLink className="h-3 w-3" />
                          {deployInstructions.repo_url}
                        </a>
                      )}
                      {deployInstructions.steps && (
                        <ol className="space-y-1 pl-4 list-decimal">
                          {deployInstructions.steps.map((step, i) => (
                            <li key={i} className="font-mono text-[11px] text-neutral-500">{step}</li>
                          ))}
                        </ol>
                      )}
                      {deployInstructions.options && (
                        <div className="space-y-3">
                          {deployInstructions.options.map((opt) => (
                            <div key={opt.provider} className="rounded border border-neutral-800 bg-neutral-950 p-3">
                              <span className="mb-1.5 block text-xs font-medium text-neutral-300">{opt.name}</span>
                              <ol className="space-y-0.5 pl-4 list-decimal">
                                {opt.steps.map((step, i) => (
                                  <li key={i} className="font-mono text-[10px] text-neutral-600">{step}</li>
                                ))}
                              </ol>
                              {opt.one_liner && (
                                <div className="mt-2 flex items-start gap-2 rounded bg-neutral-900 p-2">
                                  <Terminal className="h-3 w-3 text-neutral-600 mt-0.5 shrink-0" />
                                  <code className="break-all font-mono text-[10px] text-neutral-500">{opt.one_liner}</code>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {deployInstructions.docs_url && (
                        <a
                          href={deployInstructions.docs_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 font-mono text-[10px] text-sky-500 hover:text-sky-400"
                        >
                          <ExternalLink className="h-2.5 w-2.5" />
                          Documentation
                        </a>
                      )}
                    </div>
                  )}

                  {deployError && (
                    <div className="mt-2 flex items-start gap-2">
                      <AlertCircle className="h-3.5 w-3.5 text-red-400 mt-0.5 shrink-0" />
                      <p className="font-mono text-xs text-red-400">{deployError}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          {build.status === "deployed" && (
            <div className="relative">
              <button
                onClick={() => {
                  setShowRemixDropdown((prev) => !prev);
                  setRemixError("");
                }}
                className="flex items-center gap-2 rounded border border-sky-700 bg-sky-900/40 px-4 py-2 font-semibold text-sm text-sky-300 transition-colors hover:bg-sky-900/70"
              >
                <Shuffle className="h-4 w-4" />
                Remix
              </button>
              {showRemixDropdown && (
                <form
                  onSubmit={handleRemix}
                  className="absolute right-0 top-full z-10 mt-2 w-80 rounded-lg border border-sky-900/50 bg-neutral-900 p-4 shadow-xl"
                >
                  <div className="mb-3 flex items-center justify-between">
                    <span className="flex items-center gap-2 font-semibold text-sm text-sky-300">
                      <Shuffle className="h-3.5 w-3.5" />
                      Remix this app
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setShowRemixDropdown(false);
                        setRemixPrompt("");
                        setRemixError("");
                      }}
                      className="text-neutral-600 hover:text-neutral-400"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <input
                    type="text"
                    value={remixPrompt}
                    onChange={(e) => {
                      setRemixPrompt(e.target.value);
                      setRemixError("");
                    }}
                    placeholder="Turn this into an invoice tracker..."
                    disabled={remixing}
                    className="mb-2 w-full rounded border border-neutral-800 bg-neutral-950 px-3 py-2 font-mono text-sm text-neutral-200 placeholder:text-neutral-700 outline-none focus:border-sky-700/60 focus:ring-1 focus:ring-sky-700/30"
                    autoFocus
                  />
                  <button
                    type="submit"
                    disabled={remixing || !remixPrompt.trim()}
                    className="flex w-full items-center justify-center gap-2 rounded border border-sky-700 bg-sky-900/60 px-4 py-2 font-semibold text-sm text-sky-200 transition-colors hover:bg-sky-800/60 disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    {remixing ? (
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-sky-300 border-t-transparent" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                    Create Remix
                  </button>
                  {remixError && (
                    <p className="mt-2 font-mono text-xs text-red-400">{remixError}</p>
                  )}
                </form>
              )}
            </div>
          )}
        </div>
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

          {/* Preview / Code / Files tabs */}
          {(deployUrl || build.generated_code || projectFiles) && (
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
                {isMultiFile && projectFiles ? (
                  <button
                    onClick={() => setTab("files")}
                    className={`flex items-center gap-1.5 rounded px-3 py-1.5 font-mono text-xs transition-colors ${
                      tab === "files"
                        ? "bg-neutral-700 text-neutral-100"
                        : "text-neutral-500 hover:text-neutral-300"
                    }`}
                  >
                    <FolderOpen className="h-3 w-3" />
                    Files ({Object.keys(projectFiles).length})
                  </button>
                ) : (
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
                )}
                {isMultiFile && projectFiles && (
                  <button
                    onClick={() => setTab("code")}
                    disabled={!build.generated_code}
                    className={`rounded px-3 py-1.5 font-mono text-xs transition-colors ${
                      tab === "code"
                        ? "bg-neutral-700 text-neutral-100"
                        : "text-neutral-500 hover:text-neutral-300 disabled:opacity-30 disabled:cursor-not-allowed"
                    }`}
                  >
                    Entry HTML
                  </button>
                )}
              </div>

              {tab === "preview" && deployUrl && (
                <AppPreview url={deployUrl} hasBackend={isMultiFile} />
              )}
              {tab === "files" && projectFiles && (
                <div className="grid gap-3 lg:grid-cols-[220px_1fr]">
                  <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-3">
                    <FileExplorer
                      files={projectFiles}
                      selectedFile={selectedFile}
                      onSelectFile={setSelectedFile}
                    />
                  </div>
                  <div>
                    {selectedFile && projectFiles[selectedFile] ? (
                      <CodePreview
                        code={projectFiles[selectedFile]}
                        language={selectedFile.split(".").pop() ?? "text"}
                      />
                    ) : (
                      <div className="flex h-64 items-center justify-center rounded-lg border border-neutral-800 bg-neutral-900/40">
                        <p className="font-mono text-xs text-neutral-600">Select a file to view</p>
                      </div>
                    )}
                  </div>
                </div>
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

          {/* Error + Retry */}
          {build.status === "failed" && build.error && (
            <div className="rounded-lg border border-red-900 bg-red-950/30 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="mb-1 font-mono text-xs uppercase tracking-wider text-red-500">
                    Build Failed
                  </p>
                  <p className="font-mono text-sm text-red-400">
                    {build.error.replace(/^\[\w+\]\s*/, "")}
                  </p>
                </div>
                <button
                  onClick={async () => {
                    try {
                      await retryBuild(build.id);
                      // Restart polling — the page will auto-update
                      if (!intervalRef.current) {
                        intervalRef.current = setInterval(() => {
                          getBuild(build.id).then(setBuild).catch(() => {});
                        }, 3000);
                      }
                    } catch {}
                  }}
                  className="flex shrink-0 items-center gap-2 rounded border border-amber-700 bg-amber-900/40 px-4 py-2 font-semibold text-sm text-amber-300 transition-colors hover:bg-amber-900/70"
                >
                  <RotateCcw className="h-4 w-4" />
                  Retry
                </button>
              </div>
              <p className="mt-2 font-mono text-[10px] text-red-600">
                Retry resumes from the last successful step — no work is lost.
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

          {/* Version History */}
          {versionChain.length > 1 && (
            <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-5">
              <h3 className="mb-4 font-semibold text-sm text-neutral-300">Version History</h3>
              <VersionHistory
                currentBuildId={build.id}
                builds={versionChain}
              />
            </div>
          )}

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

          {/* Tech Stack (multi-file builds) */}
          {techStack && (
            <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-5 space-y-2">
              <h3 className="font-semibold text-sm text-neutral-300">Tech Stack</h3>
              {Object.entries(techStack).map(([key, value]) => (
                <div key={key} className="flex items-start justify-between gap-3 text-xs">
                  <span className="font-mono text-neutral-600 shrink-0 capitalize">{key}</span>
                  <span className="text-neutral-400 text-right">{value}</span>
                </div>
              ))}
            </div>
          )}

          {/* Metadata */}
          <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-5 space-y-3">
            <h3 className="font-semibold text-sm text-neutral-300">Details</h3>
            <MetaRow label="Created" value={new Date(build.created_at).toLocaleString()} />
            {build.deployed_at && (
              <MetaRow label="Deployed" value={new Date(build.deployed_at).toLocaleString()} />
            )}
            {build.complexity && (
              <MetaRow label="Complexity" value={build.complexity === "fullstack" ? "Full-stack" : build.complexity === "standard" ? "Standard" : "Simple"} />
            )}
            {build.twitter_username && (
              <MetaRow label="Requested by" value={`@${build.twitter_username}`} />
            )}
            {build.parent_build_id && (
              <MetaRow label="Type" value="Modification" />
            )}
            {projectFiles && (
              <MetaRow label="Files" value={`${Object.keys(projectFiles).length} files`} />
            )}
            {build.deploy_provider && (
              <MetaRow
                label="Cloud"
                value={`${build.deploy_provider} (${build.deploy_status ?? "unknown"})`}
              />
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
