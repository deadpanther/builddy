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
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-neutral-200">Live Build Feed</h2>
          {lastRefresh && (
            <p className="mt-0.5 font-mono text-[10px] text-neutral-700">
              Updated {lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              {" · "}auto-refresh every 5s
            </p>
          )}
        </div>
        <button
          onClick={fetchBuilds}
          className="flex items-center gap-1.5 rounded border border-neutral-800 bg-neutral-900 px-2.5 py-1.5 font-mono text-[10px] text-neutral-500 transition-colors hover:border-neutral-700 hover:text-neutral-300"
        >
          <RefreshCw className="h-3 w-3" />
          Refresh
        </button>
      </div>

      {/* Feed list */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-neutral-700">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-700 border-t-neutral-400" />
          <span className="ml-3 font-mono text-xs">Loading builds...</span>
        </div>
      ) : builds.length === 0 ? (
        <div className="rounded-lg border border-dashed border-neutral-800 py-16 text-center">
          <p className="font-mono text-sm text-neutral-600">No builds yet.</p>
          <p className="mt-1 text-xs text-neutral-700">Submit one below or tweet @builddy</p>
        </div>
      ) : (
        <div className="space-y-3">
          {builds.map((build) => (
            <BuildCard key={build.id} build={build} />
          ))}
        </div>
      )}
    </div>
  );
}
