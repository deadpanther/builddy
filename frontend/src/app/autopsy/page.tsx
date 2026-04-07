"use client";

import { useState, useEffect, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createAutopsy, listAutopsies, type AutopsySummary } from "@/lib/api";
import { GitHubRepoPicker } from "@/components/GitHubRepoPicker";

export const dynamic = "force-dynamic";

export default function AutopsyHome() {
  const router = useRouter();
  const [mode, setMode] = useState<"picker" | "url">("picker");
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [recents, setRecents] = useState<AutopsySummary[]>([]);

  useEffect(() => {
    listAutopsies().then(setRecents).catch(() => {});
  }, []);

  async function startAutopsy(url: string) {
    setLoading(true);
    setError("");
    try {
      const { autopsy_id } = await createAutopsy(url);
      router.push(`/autopsy/${autopsy_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start autopsy");
      setLoading(false);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    const urlPattern = /^https?:\/\/github\.com\/[\w.-]+\/[\w.-]+/;
    if (!urlPattern.test(repoUrl.trim())) {
      setError("Enter a valid GitHub repository URL");
      return;
    }

    await startAutopsy(repoUrl.trim());
  }

  const statusColor: Record<string, string> = {
    complete: "text-terminal-green",
    analyzing: "text-terminal-amber",
    cloning: "text-evidence-blue",
    failed: "text-terminal-red",
    pending: "text-neutral-500",
  };

  return (
    <div className="flex min-h-[calc(100vh-48px)] flex-col items-center justify-center px-4">
      <div className="stagger-children mb-12 flex flex-col items-center text-center">
        <div className="mb-6 font-mono text-xs tracking-[0.3em] text-neutral-600 uppercase">
          Forensic Code Analysis Laboratory
        </div>

        <h1 className="mb-2 font-typewriter text-5xl font-bold tracking-tight text-neutral-100 md:text-6xl">
          Code <span className="text-red-400">Autopsy</span>
        </h1>

        <p className="mb-1 font-typewriter text-lg text-neutral-500">
          Determine cause of death for any GitHub repository.
        </p>

        <p className="max-w-md text-sm text-neutral-600">
          Feed it a repo URL. Dr. GLM 5.1 will perform a full forensic examination &mdash;
          reading files, commits, issues, and PRs &mdash; then issue a death certificate.
        </p>
      </div>

      <div className="w-full max-w-2xl">
        {/* Mode tabs */}
        <div className="mb-3 flex gap-1 rounded-md border border-autopsy-border bg-autopsy-surface p-1">
          <button
            type="button"
            onClick={() => setMode("picker")}
            className={`flex flex-1 items-center justify-center gap-2 rounded px-3 py-2 font-typewriter text-xs font-bold uppercase tracking-wider transition-all ${
              mode === "picker"
                ? "bg-terminal-green/15 text-terminal-green shadow-[0_0_8px_rgba(0,255,65,0.08)]"
                : "text-neutral-600 hover:text-neutral-400"
            }`}
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
            My Repos
          </button>
          <button
            type="button"
            onClick={() => setMode("url")}
            className={`flex flex-1 items-center justify-center gap-2 rounded px-3 py-2 font-typewriter text-xs font-bold uppercase tracking-wider transition-all ${
              mode === "url"
                ? "bg-terminal-green/15 text-terminal-green shadow-[0_0_8px_rgba(0,255,65,0.08)]"
                : "text-neutral-600 hover:text-neutral-400"
            }`}
          >
            <span className="font-mono text-xs">&gt;_</span>
            Paste URL
          </button>
        </div>

        {mode === "picker" ? (
          /* ── GitHub Repo Picker (Auth0 Token Vault) ── */
          <div className="rounded-md border border-autopsy-border bg-autopsy-surface p-4">
            <div className="flex items-center gap-2 px-1 pb-3 text-xs font-mono text-neutral-600">
              <span className="terminal-glow text-[10px]">SPECIMEN</span>
              <span className="flex-1 border-b border-dashed border-autopsy-border" />
              <span>Select from GitHub via Auth0</span>
            </div>
            <GitHubRepoPicker
              onSelect={(url) => startAutopsy(url)}
              disabled={loading}
            />
          </div>
        ) : (
          /* ── Manual URL Input ── */
          <form onSubmit={handleSubmit}>
            <div className="relative rounded-md border border-autopsy-border bg-autopsy-surface p-1 transition-colors focus-within:border-terminal-green/40 focus-within:shadow-[0_0_24px_rgba(0,255,65,0.06)]">
              <div className="flex items-center gap-2 px-3 py-1 text-xs font-mono text-neutral-600">
                <span className="terminal-glow text-[10px]">SPECIMEN</span>
                <span className="flex-1 border-b border-dashed border-autopsy-border" />
                <span>GitHub Repository URL</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="pl-3 font-mono text-terminal-green/60 text-sm">&gt;</span>
                <input
                  type="url"
                  value={repoUrl}
                  onChange={(e) => { setRepoUrl(e.target.value); setError(""); }}
                  placeholder="https://github.com/owner/repo"
                  className="flex-1 bg-transparent px-1 py-3 font-mono text-sm text-neutral-200 placeholder:text-neutral-700 outline-none"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading || !repoUrl.trim()}
                  className="mr-1 rounded bg-terminal-green/90 px-5 py-2.5 font-typewriter text-xs font-bold uppercase tracking-wider text-autopsy-bg transition-all hover:bg-terminal-green hover:shadow-[0_0_16px_rgba(0,255,65,0.3)] disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-autopsy-bg border-t-transparent" />
                      Preparing...
                    </span>
                  ) : (
                    "Begin Autopsy"
                  )}
                </button>
              </div>
            </div>
          </form>
        )}

        {error && (
          <div className="mt-3 rounded border border-terminal-red/30 bg-terminal-red/5 px-4 py-2 font-mono text-xs text-terminal-red">
            {error}
          </div>
        )}

        {loading && mode === "picker" && (
          <div className="mt-3 flex items-center justify-center gap-2 rounded border border-terminal-green/20 bg-terminal-green/5 px-4 py-3">
            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-terminal-green border-t-transparent" />
            <span className="font-typewriter text-xs text-terminal-green">Preparing autopsy...</span>
          </div>
        )}
      </div>

      {recents.length > 0 && (
        <div className="mt-16 w-full max-w-2xl">
          <div className="crime-tape mb-4 inline-block rounded-sm text-[10px]">
            Recent Case Files
          </div>
          <div className="space-y-2">
            {recents.map((a) => (
              <a
                key={a.id}
                href={`/autopsy/${a.id}`}
                className="flex items-center gap-4 rounded border border-autopsy-border bg-autopsy-surface px-4 py-3 transition-colors hover:border-autopsy-border-light hover:bg-autopsy-panel"
              >
                <span className="evidence-marker text-[10px]">
                  {a.id.slice(0, 2).toUpperCase()}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-sm text-neutral-200 truncate">{a.repo_name}</div>
                  {a.cause_of_death && (
                    <div className="mt-0.5 text-xs text-neutral-500 truncate">COD: {a.cause_of_death}</div>
                  )}
                </div>
                <span className={`font-mono text-[10px] uppercase tracking-wider ${statusColor[a.status] || "text-neutral-500"}`}>
                  {a.status}
                </span>
                {a.created_at && (
                  <span className="text-[10px] text-neutral-600 font-mono">
                    {new Date(a.created_at).toLocaleDateString()}
                  </span>
                )}
              </a>
            ))}
          </div>
        </div>
      )}

      <div className="mt-20 mb-8 text-center text-[10px] text-neutral-700 font-mono tracking-wider">
        POWERED BY GLM 5.1 &bull; ZHIPU AI FORENSIC LABORATORY
      </div>
    </div>
  );
}
