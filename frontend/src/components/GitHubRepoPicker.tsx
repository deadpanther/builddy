"use client";

import { useState, useEffect } from "react";
import { useUser } from "@auth0/nextjs-auth0/client";

interface Repo {
  id: number;
  name: string;
  full_name: string;
  html_url: string;
  description: string | null;
  language: string | null;
  stargazers_count: number;
  updated_at: string;
  private: boolean;
}

interface GitHubRepoPickerProps {
  onSelect: (repoUrl: string) => void;
  disabled?: boolean;
}

const LANG_COLORS: Record<string, string> = {
  JavaScript: "#f1e05a",
  TypeScript: "#3178c6",
  Python: "#3572A5",
  Java: "#b07219",
  Go: "#00ADD8",
  Rust: "#dea584",
  Ruby: "#701516",
  PHP: "#4F5D95",
  C: "#555555",
  "C++": "#f34b7d",
  "C#": "#178600",
  Swift: "#F05138",
  Kotlin: "#A97BFF",
  Dart: "#00B4AB",
  HTML: "#e34c26",
  CSS: "#563d7c",
  Shell: "#89e051",
  Vue: "#41b883",
};

export function GitHubRepoPicker({ onSelect, disabled }: GitHubRepoPickerProps) {
  const { user, isLoading: authLoading } = useUser();
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;

    setLoading(true);
    fetch("/api/github/repos")
      .then((res) => res.json())
      .then((data) => {
        setRepos(data.repos || []);
        setConnected(data.connected ?? false);
        if (!data.connected && data.message) {
          setError(data.message);
        }
      })
      .catch(() => setError("Failed to fetch repos"))
      .finally(() => setLoading(false));
  }, [user]);

  if (authLoading) {
    return (
      <div className="flex flex-col items-center gap-3 py-8">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-terminal-green border-t-transparent" />
        <span className="font-mono text-xs text-neutral-600">Checking auth...</span>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-md border border-autopsy-border bg-autopsy-surface px-6 py-8">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-terminal-green/10">
          <svg className="h-6 w-6 text-terminal-green" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
        </div>
        <p className="font-typewriter text-sm text-neutral-400 text-center">
          Sign in to browse your GitHub repositories
        </p>
        <a
          href="/api/auth/login"
          className="rounded bg-terminal-green/90 px-5 py-2 font-typewriter text-xs font-bold uppercase tracking-wider text-autopsy-bg transition-all hover:bg-terminal-green hover:shadow-[0_0_16px_rgba(0,255,65,0.3)]"
        >
          Sign In with Auth0
        </a>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center gap-3 py-8">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-terminal-green border-t-transparent" />
        <span className="font-mono text-xs text-neutral-600">Fetching your repos...</span>
      </div>
    );
  }

  if (!connected || repos.length === 0) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-md border border-autopsy-border bg-autopsy-surface px-6 py-8">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-terminal-amber/10">
          <svg className="h-6 w-6 text-terminal-amber" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
        </div>
        <p className="font-typewriter text-sm text-neutral-400 text-center">
          {error || "Connect GitHub via Auth0 to list your repositories"}
        </p>
        <p className="font-mono text-[10px] text-neutral-600 text-center max-w-sm">
          Set up GitHub as a social connection with Token Vault in your Auth0 dashboard to enable repo browsing.
          You can still paste a URL in the manual tab.
        </p>
      </div>
    );
  }

  const filtered = repos.filter(
    (r) =>
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      r.full_name.toLowerCase().includes(search.toLowerCase()) ||
      (r.description?.toLowerCase().includes(search.toLowerCase()) ?? false)
  );

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 font-mono text-terminal-green/60 text-sm">&gt;</span>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search your repositories..."
          className="w-full bg-autopsy-surface border border-autopsy-border rounded-md pl-7 pr-3 py-2.5 font-mono text-sm text-neutral-200 placeholder:text-neutral-700 outline-none focus:border-terminal-green/40 transition-colors"
          disabled={disabled}
        />
      </div>

      {/* Repo list */}
      <div className="max-h-72 overflow-y-auto space-y-1.5 pr-1 scrollbar-thin">
        {filtered.map((repo) => (
          <button
            key={repo.id}
            type="button"
            onClick={() => onSelect(repo.html_url)}
            disabled={disabled}
            className="w-full flex items-start gap-3 rounded-md border border-autopsy-border bg-autopsy-surface px-3 py-2.5 text-left transition-all hover:border-terminal-green/30 hover:bg-terminal-green/5 hover:shadow-[0_0_12px_rgba(0,255,65,0.04)] disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm text-neutral-200 truncate group-hover:text-terminal-green transition-colors">
                  {repo.full_name}
                </span>
                {repo.private && (
                  <span className="shrink-0 rounded border border-terminal-amber/30 bg-terminal-amber/10 px-1.5 py-0.5 font-mono text-[9px] text-terminal-amber">
                    PRIVATE
                  </span>
                )}
              </div>
              {repo.description && (
                <p className="mt-0.5 text-xs text-neutral-600 truncate">{repo.description}</p>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-3 pt-0.5">
              {repo.language && (
                <span className="flex items-center gap-1 text-[10px] text-neutral-500">
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ backgroundColor: LANG_COLORS[repo.language] || "#8b8b8b" }}
                  />
                  {repo.language}
                </span>
              )}
              {repo.stargazers_count > 0 && (
                <span className="font-mono text-[10px] text-neutral-600">
                  {repo.stargazers_count}
                </span>
              )}
            </div>
          </button>
        ))}
        {filtered.length === 0 && (
          <p className="py-4 text-center font-mono text-xs text-neutral-600">
            No repos match &quot;{search}&quot;
          </p>
        )}
      </div>

      <p className="font-mono text-[10px] text-neutral-700 text-center">
        {repos.length} repos loaded via Auth0 Token Vault
      </p>
    </div>
  );
}
