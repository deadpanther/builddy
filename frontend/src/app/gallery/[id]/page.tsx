import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ExternalLink, Grid } from "lucide-react";
import { resolveDeployUrl } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type GalleryDetail = {
  id: string;
  app_name: string | null;
  app_description: string | null;
  tweet_text: string | null;
  deploy_url: string | null;
  deploy_external_url: string | null;
  thumbnail_url: string | null;
  remix_count?: number;
  complexity?: string | null;
};

type PageProps = { params: { id: string } };

async function fetchGalleryDetail(id: string): Promise<GalleryDetail | null> {
  const res = await fetch(`${API}/api/gallery/${encodeURIComponent(id)}`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) return null;
  return res.json();
}

function thumbSrc(d: GalleryDetail): string | null {
  if (!d.thumbnail_url) return null;
  return d.thumbnail_url.startsWith("http") ? d.thumbnail_url : `${API}${d.thumbnail_url}`;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const d = await fetchGalleryDetail(params.id);
  if (!d) {
    return { title: "Gallery | Builddy" };
  }
  const title = (d.app_name || "App").trim();
  const description =
    (d.app_description || d.tweet_text || "Live app built with Builddy.").slice(0, 200);
  const og = thumbSrc(d);
  return {
    title: `${title} | Builddy Gallery`,
    description,
    openGraph: {
      title,
      description,
      type: "website",
      images: og ? [{ url: og, alt: title }] : [],
    },
    twitter: {
      card: og ? "summary_large_image" : "summary",
      title,
      description,
      images: og ? [og] : [],
    },
  };
}

export default async function GalleryDetailPage({ params }: PageProps) {
  const d = await fetchGalleryDetail(params.id);
  if (!d) notFound();

  const live =
    d.deploy_external_url ||
    resolveDeployUrl(d.deploy_url) ||
    null;
  const og = thumbSrc(d);

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/gallery"
        className="mb-6 inline-flex items-center gap-2 font-mono text-xs text-neutral-500 hover:text-neutral-200"
      >
        <Grid className="h-3.5 w-3.5" />
        Gallery
      </Link>

      <div className="overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-900/60">
        <div className="aspect-video border-b border-neutral-800 bg-neutral-950">
          {og ? (
            <img
              src={og}
              alt={d.app_name || "App thumbnail"}
              className="h-full w-full object-cover object-top"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-neutral-600">
              No thumbnail
            </div>
          )}
        </div>
        <div className="p-6">
          <h1 className="text-2xl font-bold text-neutral-100">{d.app_name || "Untitled app"}</h1>
          {(d.app_description || d.tweet_text) && (
            <p className="mt-2 text-sm leading-relaxed text-neutral-400">
              {d.app_description || d.tweet_text}
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            {live && (
              <a
                href={live}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-violet-700/50 bg-violet-950/40 px-4 py-2 text-sm font-medium text-violet-200 hover:bg-violet-950/70"
              >
                <ExternalLink className="h-4 w-4" />
                Open live app
              </a>
            )}
            <Link
              href={`/build/${d.id}`}
              className="inline-flex items-center gap-2 rounded-lg border border-neutral-700 px-4 py-2 text-sm text-neutral-300 hover:border-neutral-500"
            >
              Build details
            </Link>
          </div>
          {(d.remix_count ?? 0) > 0 && (
            <p className="mt-4 font-mono text-xs text-neutral-600">
              Remixed {d.remix_count} time{d.remix_count !== 1 ? "s" : ""}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
