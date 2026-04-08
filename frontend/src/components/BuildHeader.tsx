"use client";

import Link from "next/link";
import { ArrowLeft, ExternalLink, Download } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { getDownloadUrl, resolveDeployUrl } from "@/lib/api";
import type { Build } from "@/lib/types";

interface BuildHeaderProps {
  build: Build;
  children?: React.ReactNode; // For action buttons like CloudDeploy, Remix
}

export function BuildHeader({ build, children }: BuildHeaderProps) {
  const deployUrl = build.deploy_url ? resolveDeployUrl(build.deploy_url) : null;
  const isActive = ["pending", "planning", "coding", "reviewing", "deploying"].includes(build.status);

  return (
    <>
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
            {build.complexity && build.complexity !== "simple" && (
              <span className="rounded bg-neutral-900 px-2 py-0.5 font-mono text-[10px] text-neutral-500">
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
          {build.tweet_url && (
            <div className="mt-1">
              <Link
                href={build.tweet_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-xs text-sky-500 hover:text-sky-400"
              >
                View original
              </Link>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0 relative flex-wrap">
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
          {children}
        </div>
      </div>
    </>
  );
}
