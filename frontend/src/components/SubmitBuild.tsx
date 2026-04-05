"use client";

import { useState, type FormEvent } from "react";
import { Send, Sparkles, CheckCircle } from "lucide-react";
import { createBuild } from "@/lib/api";
import { cn } from "@/lib/utils";

const EXAMPLE_PROMPTS = [
  "a Pomodoro timer with session tracking",
  "a color palette generator from image",
  "a simple markdown editor with preview",
  "a BMI calculator with health tips",
  "a CSS gradient generator",
];

interface SubmitBuildProps {
  onBuildCreated?: (buildId: string) => void;
}

export function SubmitBuild({ onBuildCreated }: SubmitBuildProps) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed) return;

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const build = await createBuild(trimmed);
      setPrompt("");
      setSuccess(build.app_name ?? "Build");
      onBuildCreated?.(build.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start build");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-5">
      <div className="mb-4 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-violet-400" />
        <h2 className="font-semibold text-neutral-200 text-sm">Manual Build</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-wider text-neutral-600">
            Describe your app
          </label>
          <textarea
            value={prompt}
            onChange={(e) => {
              setPrompt(e.target.value);
              setError("");
              setSuccess("");
            }}
            placeholder="Build me a Pomodoro timer with dark mode..."
            rows={4}
            disabled={loading}
            className={cn(
              "w-full resize-none rounded border border-neutral-800 bg-neutral-950 px-3 py-2 font-mono text-sm text-neutral-200 placeholder:text-neutral-700 outline-none transition-colors",
              "focus:border-violet-700/60 focus:ring-1 focus:ring-violet-700/30",
              loading && "opacity-50 cursor-not-allowed"
            )}
          />
        </div>

        {/* Example prompts */}
        <div>
          <p className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-neutral-700">
            Quick examples
          </p>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_PROMPTS.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => setPrompt(`Build me ${ex}`)}
                className="rounded border border-neutral-800 bg-neutral-900 px-2 py-0.5 font-mono text-[10px] text-neutral-500 transition-colors hover:border-neutral-700 hover:text-neutral-300"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded border px-4 py-2.5 font-semibold text-sm transition-all",
            "border-violet-700 bg-violet-900/60 text-violet-200 hover:bg-violet-800/60",
            "disabled:opacity-30 disabled:cursor-not-allowed"
          )}
        >
          {loading ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-violet-300 border-t-transparent" />
              Building...
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              Start Build
            </>
          )}
        </button>

        {success && (
          <div className="flex items-center gap-2 rounded border border-emerald-900 bg-emerald-950/50 px-3 py-2">
            <CheckCircle className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
            <p className="font-mono text-xs text-emerald-400">
              Build started! Check the feed for progress.
            </p>
          </div>
        )}
        {error && (
          <p className="rounded border border-red-900 bg-red-950/50 px-3 py-2 font-mono text-xs text-red-400">
            {error}
          </p>
        )}
      </form>
    </div>
  );
}
