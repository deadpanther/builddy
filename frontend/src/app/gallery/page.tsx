"use client";

import { useEffect, useState } from "react";
import { ExternalLink, Grid, Search } from "lucide-react";
import { getGallery, resolveDeployUrl } from "@/lib/api";
import type { GalleryApp } from "@/lib/types";

export default function GalleryPage() {
  const [apps, setApps] = useState<GalleryApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    getGallery()
      .then(setApps)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = query
    ? apps.filter(
        (a) =>
          a.app_name.toLowerCase().includes(query.toLowerCase()) ||
          a.app_description?.toLowerCase().includes(query.toLowerCase())
      )
    : apps;

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

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-700 border-t-neutral-400" />
          <span className="ml-3 font-mono text-sm text-neutral-600">Loading gallery...</span>
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
  const url = resolveDeployUrl(app.deploy_url);

  return (
    <div className="group rounded-lg border border-neutral-800 bg-neutral-900/50 p-4 transition-all hover:border-neutral-600 hover:bg-neutral-900">
      {/* Thumbnail placeholder */}
      <div className="mb-3 flex h-32 items-center justify-center rounded border border-neutral-800 bg-neutral-950 overflow-hidden">
        {url ? (
          <iframe
            src={url}
            className="pointer-events-none h-full w-full origin-center"
            title={app.app_name}
            sandbox="allow-scripts allow-same-origin"
            style={{ transform: "scale(0.5)", width: "200%", height: "200%", marginLeft: "-50%", marginTop: "-50%" }}
          />
        ) : (
          <span className="font-mono text-xs text-neutral-700">No preview</span>
        )}
      </div>

      <h3 className="font-semibold text-neutral-100 truncate">{app.app_name}</h3>

      {app.app_description && (
        <p className="mt-1 text-xs text-neutral-500 line-clamp-2 leading-relaxed">
          {app.app_description}
        </p>
      )}

      <div className="mt-3 flex items-center justify-between">
        <span className="font-mono text-[10px] text-neutral-700">
          {new Date(app.deployed_at).toLocaleDateString()}
        </span>
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
      </div>
    </div>
  );
}
