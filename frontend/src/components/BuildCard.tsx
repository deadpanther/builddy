import Link from "next/link";
import { ExternalLink, Clock, User } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import { resolveDeployUrl } from "@/lib/api";
import type { Build } from "@/lib/types";

interface BuildCardProps {
  build: Build;
}

export function BuildCard({ build }: BuildCardProps) {
  const isActive = ["pending", "planning", "coding", "reviewing", "deploying"].includes(build.status);

  return (
    <Link
      href={`/build/${build.id}`}
      className="group block rounded-lg border border-neutral-800 bg-neutral-900/50 p-4 transition-all hover:border-neutral-600 hover:bg-neutral-900"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {build.app_name ? (
            <div className="mb-1 font-semibold text-neutral-100 truncate">
              {build.app_name}
            </div>
          ) : (
            <div className="mb-1 font-semibold text-neutral-500 truncate italic text-sm">
              Building...
            </div>
          )}
          <p className="text-sm text-neutral-400 line-clamp-2 leading-relaxed">
            {build.tweet_text || build.prompt || "No description"}
          </p>
        </div>
        <StatusBadge status={build.status} />
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-neutral-600">
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
            <span className="flex items-center gap-1 text-emerald-500">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live
            </span>
          )}
        </div>

        {resolveDeployUrl(build.deploy_url) && (
          <a
            href={resolveDeployUrl(build.deploy_url)!}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 rounded border border-emerald-800 bg-emerald-950 px-2 py-0.5 font-mono text-[10px] text-emerald-400 transition-colors hover:bg-emerald-900"
          >
            <ExternalLink className="h-3 w-3" />
            Open App
          </a>
        )}
      </div>
    </Link>
  );
}
