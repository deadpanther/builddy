"use client";

import { useState, useEffect, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createAutopsy, listAutopsies, type AutopsySummary } from "@/lib/api";

export default function AutopsyHome() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [recents, setRecents] = useState<AutopsySummary[]>([]);

  useEffect(() => {
    listAutopsies().then(setRecents).catch(() => {});
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    const urlPattern = /^https?:\/\/github\.com\/[\w.-]+\/[\w.-]+/;
    if (!urlPattern.test(repoUrl.trim())) {
      setError("Enter a valid GitHub repository URL");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const { autopsy_id } = await createAutopsy(repoUrl.trim());
      router.push(`/autopsy/${autopsy_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start autopsy");
      setLoading(false);
    }
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

      <form onSubmit={handleSubmit} className="w-full max-w-2xl">
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

        {error && (
          <div className="mt-3 rounded border border-terminal-red/30 bg-terminal-red/5 px-4 py-2 font-mono text-xs text-terminal-red">
            {error}
          </div>
        )}
      </form>

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
