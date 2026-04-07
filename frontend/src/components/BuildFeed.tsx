"use client";

import { useEffect, useState, useCallback } from "react";
import { RefreshCw } from "lucide-react";
import { getBuilds } from "@/lib/api";
import { BuildCard } from "./BuildCard";
import type { Build } from "@/lib/types";

interface BuildFeedProps {
  refreshTrigger?: number;
}

export function BuildFeed({ refreshTrigger }: BuildFeedProps) {
  const [builds, setBuilds] = useState<Build[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchBuilds = useCallback(async () => {
    try {
      const data = await getBuilds();
      setBuilds(data);
      setLastRefresh(new Date());
    } catch {
      // keep previous data on error
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + auto-refresh every 5s
  useEffect(() => {
    fetchBuilds();
    const interval = setInterval(fetchBuilds, 5000);
    return () => clearInterval(interval);
  }, [fetchBuilds]);

  // Refresh when a new build is submitted
  useEffect(() => {
    if (refreshTrigger) fetchBuilds();
  }, [refreshTrigger, fetchBuilds]);

  return (
    <div>
      {/* Feed header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Live Build Feed</h2>
          {lastRefresh && (
            <p className="mt-0.5 font-mono text-[10px] text-zinc-600">
              Updated {lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              {" · "}auto-refresh every 5s
            </p>
          )}
        </div>
        <button
          onClick={fetchBuilds}
          className="flex items-center gap-1.5 rounded-lg border border-stroke bg-surface-100 px-3 py-1.5 font-mono text-xs text-zinc-500 transition-all hover:border-stroke-hover hover:text-white hover:bg-surface-200"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>

      {/* Feed list */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-600">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-700 border-t-brand-400" />
          <span className="ml-3 font-mono text-xs">Loading builds...</span>
        </div>
      ) : builds.length === 0 ? (
        <div className="glass-panel py-20 text-center">
          <p className="text-sm text-zinc-500">No builds yet.</p>
          <p className="mt-1 text-xs text-zinc-600">Submit one on the right or tweet @builddy</p>
        </div>
      ) : (
        <div className="space-y-4 stagger-children">
          {builds.map((build) => (
            <BuildCard key={build.id} build={build} />
          ))}
        </div>
      )}
    </div>
  );
}
