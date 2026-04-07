"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  ExternalLink,
  Grid,
  Search,
  Shuffle,
  Layers,
  TrendingUp,
  Clock,
  Send,
  X,
} from "lucide-react";
import { getGallery, resolveDeployUrl, remixBuild, API_BASE } from "@/lib/api";
import type { GalleryApp } from "@/lib/types";

type SortOption = "recent" | "trending";

export default function GalleryPage() {
  const [apps, setApps] = useState<GalleryApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortOption>("recent");

  useEffect(() => {
    getGallery()
      .then(setApps)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = (() => {
    const searched = query
      ? apps.filter(
          (a) =>
            a.app_name.toLowerCase().includes(query.toLowerCase()) ||
            a.app_description?.toLowerCase().includes(query.toLowerCase())
        )
      : apps;

    if (sort === "trending") {
      return [...searched].sort(
        (a, b) => (b.remix_count ?? 0) - (a.remix_count ?? 0)
      );
    }
    return searched;
  })();

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Grid className="h-5 w-5 text-violet-400" />
          <h1 className="text-xl font-bold text-neutral-100">App Gallery</h1>
          {!loading && (
            <span className="rounded-full border border-neutral-700 bg-neutral-800 px-2 py-0.5 font-mono text-xs text-neutral-400">
              {apps.length}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Sort toggle */}
          <div className="flex rounded-lg border border-neutral-800 bg-neutral-900 p-0.5">
            <button
              onClick={() => setSort("recent")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-mono text-xs transition-colors ${
                sort === "recent"
                  ? "bg-neutral-700 text-neutral-100"
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              <Clock className="h-3 w-3" />
              Recent
            </button>
            <button
              onClick={() => setSort("trending")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-mono text-xs transition-colors ${
                sort === "trending"
                  ? "bg-neutral-700 text-neutral-100"
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              <TrendingUp className="h-3 w-3" />
              Trending
            </button>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-neutral-600" />
            <input
              type="text"
              placeholder="Search apps..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="rounded-lg border border-neutral-800 bg-neutral-900 pl-9 pr-4 py-2 font-mono text-sm text-neutral-300 placeholder:text-neutral-700 outline-none focus:border-neutral-600"
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-700 border-t-neutral-400" />
          <span className="ml-3 font-mono text-sm text-neutral-600">
            Loading gallery...
          </span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border border-dashed border-neutral-800 py-24 text-center">
          <p className="font-mono text-neutral-600">
            {query ? "No apps match your search." : "No deployed apps yet."}
          </p>
          <p className="mt-1 text-sm text-neutral-700">
            {!query && "Tweet @builddy with your app idea!"}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((app) => (
            <GalleryCard key={app.id} app={app} />
          ))}
        </div>
      )}
    </div>
  );
}

function GalleryCard({ app }: { app: GalleryApp }) {
  const router = useRouter();
  const url = resolveDeployUrl(app.deploy_url);
  const [showRemixForm, setShowRemixForm] = useState(false);
  const [remixPrompt, setRemixPrompt] = useState("");
  const [remixing, setRemixing] = useState(false);
  const [remixError, setRemixError] = useState("");

  const handleRemixSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!remixPrompt.trim()) return;

    setRemixing(true);
    setRemixError("");
    try {
      const newBuild = await remixBuild(app.id, remixPrompt.trim());
      router.push(`/build/${newBuild.id}`);
    } catch (err) {
      setRemixError(
        err instanceof Error ? err.message : "Failed to remix"
      );
    } finally {
      setRemixing(false);
    }
  };

  const handleRemixClose = () => {
    setShowRemixForm(false);
    setRemixPrompt("");
    setRemixError("");
  };

  const complexityLabel =
    app.complexity === "fullstack"
      ? "Full-stack"
      : app.complexity === "standard"
        ? "Standard"
        : null;

  return (
    <div className="group rounded-lg border border-neutral-800 bg-neutral-900/50 p-4 transition-all hover:border-neutral-600 hover:bg-neutral-900">
      {/* Thumbnail */}
      <div className="mb-3 overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950 aspect-video">
        {app.thumbnail_url ? (
          <img
            src={app.thumbnail_url.startsWith("http") ? app.thumbnail_url : `${API_BASE}${app.thumbnail_url}`}
            alt={app.app_name}
            className="h-full w-full object-cover object-top"
          />
        ) : url ? (
          <iframe
            src={url}
            className="pointer-events-none h-full w-full origin-center"
            title={app.app_name}
            sandbox="allow-scripts allow-same-origin"
            style={{
              transform: "scale(0.5)",
              width: "200%",
              height: "200%",
              marginLeft: "-50%",
              marginTop: "-50%",
            }}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <span className="font-mono text-xs text-neutral-700">No preview</span>
          </div>
        )}
      </div>

      {/* Title + badges */}
      <div className="flex items-start gap-2">
        <h3 className="flex-1 font-semibold text-neutral-100 truncate">
          {app.app_name}
        </h3>
        {complexityLabel && (
          <span className="flex shrink-0 items-center gap-1 rounded border border-violet-800 bg-violet-950/50 px-1.5 py-0.5 font-mono text-[10px] text-violet-400">
            <Layers className="h-2.5 w-2.5" />
            {complexityLabel}
          </span>
        )}
      </div>

      {app.app_description && (
        <p className="mt-1 text-xs text-neutral-500 line-clamp-2 leading-relaxed">
          {app.app_description}
        </p>
      )}

      {/* Remix count badge + date */}
      <div className="mt-2 flex items-center gap-2">
        <span className="font-mono text-[10px] text-neutral-700">
          {new Date(app.deployed_at).toLocaleDateString()}
        </span>
        {(app.remix_count ?? 0) > 0 && (
          <span className="flex items-center gap-1 rounded-full border border-amber-800/50 bg-amber-950/30 px-2 py-0.5 font-mono text-[10px] text-amber-400">
            <Shuffle className="h-2.5 w-2.5" />
            Remixed {app.remix_count} time{app.remix_count !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="mt-3 flex items-center gap-2">
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded border border-neutral-700 bg-neutral-800 px-2.5 py-1 font-mono text-[10px] text-neutral-400 transition-colors hover:border-neutral-600 hover:text-neutral-200"
          >
            <ExternalLink className="h-3 w-3" />
            Open
          </a>
        )}
        <button
          onClick={() => setShowRemixForm((prev) => !prev)}
          className="flex items-center gap-1.5 rounded border border-sky-800 bg-sky-950/40 px-2.5 py-1 font-mono text-[10px] text-sky-400 transition-colors hover:border-sky-600 hover:text-sky-200"
        >
          <Shuffle className="h-3 w-3" />
          Remix
        </button>
      </div>

      {/* Inline remix form */}
      {showRemixForm && (
        <form
          onSubmit={handleRemixSubmit}
          className="mt-3 rounded border border-sky-900/50 bg-sky-950/20 p-3"
        >
          <div className="mb-2 flex items-center justify-between">
            <span className="font-mono text-[10px] text-sky-400">
              Remix this app
            </span>
            <button
              type="button"
              onClick={handleRemixClose}
              className="text-neutral-600 hover:text-neutral-400"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={remixPrompt}
              onChange={(e) => {
                setRemixPrompt(e.target.value);
                setRemixError("");
              }}
              placeholder="Turn this into..."
              disabled={remixing}
              className="flex-1 rounded border border-neutral-800 bg-neutral-950 px-2 py-1.5 font-mono text-xs text-neutral-200 placeholder:text-neutral-700 outline-none focus:border-sky-700/60"
            />
            <button
              type="submit"
              disabled={remixing || !remixPrompt.trim()}
              className="flex items-center gap-1 rounded border border-sky-700 bg-sky-900/60 px-2.5 py-1.5 font-mono text-xs text-sky-200 transition-colors hover:bg-sky-800/60 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {remixing ? (
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-sky-300 border-t-transparent" />
              ) : (
                <Send className="h-3 w-3" />
              )}
            </button>
          </div>
          {remixError && (
            <p className="mt-1.5 font-mono text-[10px] text-red-400">
              {remixError}
            </p>
          )}
        </form>
      )}
    </div>
  );
}
