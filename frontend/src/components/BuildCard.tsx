import Link from "next/link";
import { ExternalLink, Clock, User, Image, Download, Layers } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import { resolveDeployUrl, getDownloadUrl } from "@/lib/api";
import type { Build } from "@/lib/types";

interface BuildCardProps {
  build: Build;
}

export function BuildCard({ build }: BuildCardProps) {
  const isActive = ["pending", "planning", "coding", "reviewing", "deploying"].includes(build.status);

  return (
    <Link
      href={`/build/${build.id}`}
      className="group glass-panel shine-hover block p-5 transition-all hover:shadow-glass-hover"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {build.app_name ? (
            <div className="mb-1 text-base font-semibold text-white truncate group-hover:text-gradient transition-colors">
              {build.app_name}
            </div>
          ) : (
            <div className="mb-1 text-sm font-semibold text-zinc-600 truncate italic">
              Building...
            </div>
          )}
          <p className="text-sm text-zinc-400 line-clamp-2 leading-relaxed">
            {build.tweet_text || build.prompt || "No description"}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {build.build_type === "screenshot" && (
            <span className="flex items-center gap-1 rounded-md bg-info-dim border border-info-border px-2 py-0.5 font-mono text-[10px] text-info">
              <Image className="h-2.5 w-2.5" />
              5V
            </span>
          )}
          {build.complexity && build.complexity !== "simple" && (
            <span className="flex items-center gap-1 rounded-md bg-brand-500/10 border border-brand-500/20 px-2 py-0.5 font-mono text-[10px] text-brand-300">
              <Layers className="h-2.5 w-2.5" />
              {build.complexity === "fullstack" ? "Full-stack" : "Standard"}
            </span>
          )}
          <StatusBadge status={build.status} />
        </div>
      </div>

      {/* Thumbnail */}
      {build.thumbnail_url && (
        <div className="mb-3 overflow-hidden rounded-lg border border-stroke">
          <img src={build.thumbnail_url} alt="" className="h-16 w-full object-cover" />
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-zinc-500">
          {build.twitter_username && (
            <span className="flex items-center gap-1">
              <User className="h-3 w-3" />
              @{build.twitter_username}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {new Date(build.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
          {isActive && (
            <span className="flex items-center gap-1.5 text-success">
              <span className="live-dot" />
              Live
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {resolveDeployUrl(build.deploy_url) && (
            <a
              href={resolveDeployUrl(build.deploy_url)!}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1.5 rounded-lg bg-success-dim border border-success-border px-2.5 py-1 font-mono text-[10px] text-success transition-colors hover:bg-success/20"
            >
              <ExternalLink className="h-3 w-3" />
              Open App
            </a>
          )}
          {build.zip_url && (
            <a
              href={getDownloadUrl(build.id)}
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1.5 rounded-lg bg-brand-500/10 border border-brand-500/20 px-2.5 py-1 font-mono text-[10px] text-brand-300 transition-colors hover:bg-brand-500/20"
            >
              <Download className="h-3 w-3" />
              Zip
            </a>
          )}
        </div>
      </div>
    </Link>
  );
}
