"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createBuild, createBuildFromTemplate } from "@/lib/api";

export function EmbedForm() {
  const router = useRouter();
  const sp = useSearchParams();
  const initialPrompt = sp.get("prompt") || "";
  const templateSlug = sp.get("template") || "";

  const [prompt, setPrompt] = useState(initialPrompt);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (templateSlug.trim()) {
      setLoading(true);
      try {
        const b = await createBuildFromTemplate(templateSlug.trim());
        router.push(`/build/${b.id}`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed");
      } finally {
        setLoading(false);
      }
      return;
    }
    const text = prompt.trim();
    if (text.length < 4) {
      setError("Describe your app (or pass ?template=slug).");
      return;
    }
    setLoading(true);
    try {
      const b = await createBuild(text);
      router.push(`/build/${b.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[320px] bg-neutral-950 p-4 text-neutral-100">
      <p className="mb-3 font-mono text-[10px] uppercase tracking-wider text-neutral-500">
        Builddy embed
      </p>
      <form onSubmit={onSubmit} className="space-y-2">
        {!templateSlug && (
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Build me a landing page for…"
            rows={4}
            disabled={loading}
            className="w-full resize-none rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-violet-600"
          />
        )}
        {templateSlug && (
          <p className="text-sm text-neutral-400">
            Starting from template <span className="font-mono text-violet-400">{templateSlug}</span>
          </p>
        )}
        {error && <p className="text-xs text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-violet-600 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? "Starting…" : templateSlug ? "Start from template" : "Start build"}
        </button>
      </form>
    </div>
  );
}
