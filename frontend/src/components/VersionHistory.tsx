"use client";

import Link from "next/link";
import { GitBranch, History } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { cn } from "@/lib/utils";
import type { VersionEntry } from "@/lib/types";
import type { BuildStatus } from "@/lib/types";

interface VersionHistoryProps {
  currentBuildId: string;
  builds: VersionEntry[];
  className?: string;
}

function truncatePrompt(prompt: string | undefined, maxLen = 60): string {
  if (!prompt) return "Initial build";
  if (prompt.length <= maxLen) return prompt;
  return `${prompt.slice(0, maxLen)}...`;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function VersionHistory({ currentBuildId, builds, className }: VersionHistoryProps) {
  // Builds arrive oldest-first (chain order); display newest at top
  const ordered = [...builds].reverse();

  return (
    <div className={cn("relative", className)}>
      <div className="mb-3 flex items-center gap-2 text-neutral-500">
        <History className="h-3.5 w-3.5" />
        <span className="font-mono text-[10px] uppercase tracking-wider">
          {ordered.length} version{ordered.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="space-y-0">
        {ordered.map((entry, i) => {
          const isCurrent = entry.id === currentBuildId;
          const versionNumber = ordered.length - i;
          const isLast = i === ordered.length - 1;

          return (
            <div key={entry.id} className="group relative flex gap-3">
              {/* Timeline connector */}
              <div className="flex flex-col items-center">
                {/* Dot */}
                <div
                  className={cn(
                    "mt-1 h-2.5 w-2.5 shrink-0 rounded-full border-2",
                    isCurrent
                      ? "border-violet-500 bg-violet-500"
                      : "border-neutral-600 bg-neutral-900"
                  )}
                />
                {/* Line */}
                {!isLast && (
                  <div
                    className={cn(
                      "w-0.5 flex-1",
                      isCurrent ? "bg-violet-700/50" : "bg-neutral-800"
                    )}
                    style={{ minHeight: "24px" }}
                  />
                )}
              </div>

              {/* Entry content */}
              <Link
                href={`/build/${entry.id}`}
                className={cn(
                  "mb-2 flex-1 rounded-md border-l-2 px-3 py-2 transition-colors",
                  isCurrent
                    ? "border-l-violet-500 bg-violet-900/20"
                    : "border-l-neutral-700 bg-transparent hover:bg-neutral-800/40"
                )}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "font-mono text-[10px] font-bold uppercase",
                      isCurrent ? "text-violet-400" : "text-neutral-600"
                    )}
                  >
                    v{versionNumber}
                  </span>
                  {isCurrent && (
                    <span className="font-mono text-[10px] text-violet-500">current</span>
                  )}
                  <StatusBadge status={entry.status as BuildStatus} className="ml-auto scale-90 origin-right" />
                </div>

                <p
                  className={cn(
                    "mt-1 text-sm leading-snug",
                    isCurrent ? "text-neutral-200" : "text-neutral-400"
                  )}
                >
                  {truncatePrompt(entry.prompt)}
                </p>

                <span className="mt-1 block font-mono text-xs text-neutral-600">
                  {formatTimestamp(entry.created_at)}
                </span>

                {/* Remix from here button — visible on hover for non-current versions */}
                {!isCurrent && (
                  <span
                    className="mt-1.5 hidden items-center gap-1 font-mono text-[10px] text-violet-500 group-hover:inline-flex"
                  >
                    <GitBranch className="h-3 w-3" />
                    Remix from here
                  </span>
                )}
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
