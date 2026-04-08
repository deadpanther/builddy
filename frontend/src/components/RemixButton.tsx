"use client";

import { useState, type FormEvent } from "react";
import { Shuffle, X, Loader2 } from "lucide-react";
import { remixBuild } from "@/lib/api";
import type { Build } from "@/lib/types";

interface RemixButtonProps {
  build: Build;
  onRemix: (newBuildId: string) => void;
}

export function RemixButton({ build, onRemix }: RemixButtonProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [remixing, setRemixing] = useState(false);
  const [error, setError] = useState("");

  const handleRemix = async (e: FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setRemixing(true);
    setError("");
    try {
      const newBuild = await remixBuild(build.id, prompt.trim());
      onRemix(newBuild.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remix");
    } finally {
      setRemixing(false);
    }
  };

  if (build.status !== "deployed") return null;

  return (
    <div className="relative">
      <button
        onClick={() => {
          setShowDropdown((prev) => !prev);
          setError("");
        }}
        className="flex items-center gap-2 rounded border border-sky-700 bg-sky-900/40 px-4 py-2 font-semibold text-sm text-sky-300 transition-colors hover:bg-sky-900/70"
      >
        <Shuffle className="h-4 w-4" />
        Remix
      </button>
      {showDropdown && (
        <form
          onSubmit={handleRemix}
          className="absolute right-0 top-full z-10 mt-2 w-80 rounded-lg border border-sky-900/50 bg-neutral-900 p-4 shadow-xl"
        >
          <div className="mb-3 flex items-center justify-between">
            <span className="flex items-center gap-2 font-semibold text-sm text-sky-300">
              <Shuffle className="h-3.5 w-3.5" />
              Remix this app
            </span>
            <button
              type="button"
              onClick={() => {
                setShowDropdown(false);
                setPrompt("");
                setError("");
              }}
              className="text-neutral-600 hover:text-neutral-400"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe a new variation..."
            className="mb-2 w-full rounded border border-neutral-800 bg-neutral-950 px-3 py-2 font-mono text-sm text-neutral-300 placeholder:text-neutral-600 focus:border-sky-700 focus:outline-none"
            disabled={remixing}
          />
          <button
            type="submit"
            disabled={remixing || !prompt.trim()}
            className="w-full rounded bg-sky-800 px-3 py-2 font-semibold text-sm text-sky-100 transition-colors hover:bg-sky-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {remixing ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Remixing...
              </span>
            ) : (
              "Create Remix"
            )}
          </button>
          {error && (
            <p className="mt-2 font-mono text-xs text-red-400">{error}</p>
          )}
        </form>
      )}
    </div>
  );
}
