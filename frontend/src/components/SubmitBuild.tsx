"use client";

import { useState, useRef, useCallback, type FormEvent, type DragEvent } from "react";
import { Send, Sparkles, CheckCircle, Image, Type, Upload, X } from "lucide-react";
import { createBuild, createBuildFromImage } from "@/lib/api";
import { cn } from "@/lib/utils";

const EXAMPLE_PROMPTS = [
  "a Pomodoro timer with session tracking",
  "a color palette generator",
  "a simple markdown editor with preview",
  "a BMI calculator with health tips",
  "a CSS gradient generator",
];

interface SubmitBuildProps {
  onBuildCreated?: (buildId: string) => void;
}

export function SubmitBuild({ onBuildCreated }: SubmitBuildProps) {
  const [mode, setMode] = useState<"text" | "screenshot">("text");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Screenshot state — supports multiple images
  const [images, setImages] = useState<{ base64: string; preview: string }[]>([]);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback((files: FileList | File[]) => {
    const fileArr = Array.from(files);
    for (const file of fileArr) {
      if (!file.type.startsWith("image/")) {
        setError("Please upload image files (PNG, JPG, etc.)");
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        setError("Each image must be under 5MB");
        return;
      }
    }
    setError("");
    for (const file of fileArr) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const dataUrl = e.target?.result as string;
        setImages((prev) => [...prev, { base64: dataUrl.split(",")[1], preview: dataUrl }]);
      };
      reader.readAsDataURL(file);
    }
  }, []);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const handleSubmitText = async (e: FormEvent) => {
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

  const handleSubmitScreenshot = async (e: FormEvent) => {
    e.preventDefault();
    if (images.length === 0) return;

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const b64List = images.map((img) => img.base64);
      // Send single string or array depending on count
      const imagePayload = b64List.length === 1 ? b64List[0] : b64List;
      const build = await createBuildFromImage(imagePayload, prompt);
      setImages([]);
      setPrompt("");
      setSuccess(build.app_name ?? "Screenshot Build");
      onBuildCreated?.(build.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start screenshot build");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-5">
      <div className="mb-4 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-violet-400" />
        <h2 className="font-semibold text-neutral-200 text-sm">Build an App</h2>
      </div>

      {/* Mode tabs */}
      <div className="mb-4 flex gap-1 rounded-lg border border-neutral-800 bg-neutral-950 p-1">
        <button
          type="button"
          onClick={() => setMode("text")}
          className={cn(
            "flex flex-1 items-center justify-center gap-1.5 rounded px-3 py-1.5 font-mono text-xs transition-colors",
            mode === "text"
              ? "bg-violet-900/60 text-violet-200"
              : "text-neutral-500 hover:text-neutral-300"
          )}
        >
          <Type className="h-3 w-3" />
          Describe
        </button>
        <button
          type="button"
          onClick={() => setMode("screenshot")}
          className={cn(
            "flex flex-1 items-center justify-center gap-1.5 rounded px-3 py-1.5 font-mono text-xs transition-colors",
            mode === "screenshot"
              ? "bg-violet-900/60 text-violet-200"
              : "text-neutral-500 hover:text-neutral-300"
          )}
        >
          <Image className="h-3 w-3" />
          Screenshot
        </button>
      </div>

      {mode === "text" ? (
        /* ── Text mode ──────────────────────────────────────────── */
        <form onSubmit={handleSubmitText} className="space-y-3">
          <div>
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-wider text-neutral-600">
              Describe your app
            </label>
            <textarea
              value={prompt}
              onChange={(e) => { setPrompt(e.target.value); setError(""); setSuccess(""); }}
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
                Building with GLM 5.1...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Start Build
              </>
            )}
          </button>
        </form>
      ) : (
        /* ── Screenshot mode ────────────────────────────────────── */
        <form onSubmit={handleSubmitScreenshot} className="space-y-3">
          {/* Image upload / preview area */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            {images.length === 0 ? (
              <div
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-8 transition-colors",
                  dragging
                    ? "border-violet-500 bg-violet-950/30"
                    : "border-neutral-700 bg-neutral-950 hover:border-neutral-600"
                )}
              >
                <Upload className="mb-2 h-8 w-8 text-neutral-600" />
                <p className="text-sm text-neutral-400">
                  Drop screenshot(s) or mockup(s) here
                </p>
                <p className="mt-1 font-mono text-[10px] text-neutral-600">
                  PNG, JPG up to 5MB each — upload multiple for multi-screen apps
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex flex-wrap gap-2">
                  {images.map((img, i) => (
                    <div key={i} className="relative group">
                      <img
                        src={img.preview}
                        alt={`Screenshot ${i + 1}`}
                        className="h-24 w-auto rounded border border-neutral-700 object-contain"
                      />
                      <button
                        type="button"
                        onClick={() => setImages((prev) => prev.filter((_, idx) => idx !== i))}
                        className="absolute -right-1 -top-1 rounded-full bg-red-900 p-0.5 text-red-300 opacity-0 transition-opacity group-hover:opacity-100"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                  {/* Add more button */}
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex h-24 w-20 items-center justify-center rounded border-2 border-dashed border-neutral-700 text-neutral-600 transition-colors hover:border-neutral-500 hover:text-neutral-400"
                  >
                    <span className="text-2xl">+</span>
                  </button>
                </div>
                <p className="font-mono text-[10px] text-neutral-600">
                  {images.length} screenshot{images.length !== 1 ? "s" : ""} — each becomes a screen in your app
                </p>
              </div>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) handleFiles(e.target.files);
              e.target.value = "";
            }}
          />

          <div>
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-wider text-neutral-600">
              Additional instructions (optional)
            </label>
            <input
              type="text"
              value={prompt}
              onChange={(e) => { setPrompt(e.target.value); setError(""); }}
              placeholder="Make all buttons functional, add dark mode..."
              disabled={loading}
              className={cn(
                "w-full rounded border border-neutral-800 bg-neutral-950 px-3 py-2 font-mono text-sm text-neutral-200 placeholder:text-neutral-700 outline-none transition-colors",
                "focus:border-violet-700/60 focus:ring-1 focus:ring-violet-700/30",
                loading && "opacity-50 cursor-not-allowed"
              )}
            />
          </div>

          <button
            type="submit"
            disabled={loading || images.length === 0}
            className={cn(
              "flex w-full items-center justify-center gap-2 rounded border px-4 py-2.5 font-semibold text-sm transition-all",
              "border-violet-700 bg-violet-900/60 text-violet-200 hover:bg-violet-800/60",
              "disabled:opacity-30 disabled:cursor-not-allowed"
            )}
          >
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-violet-300 border-t-transparent" />
                GLM-5V Analyzing Screenshot...
              </>
            ) : (
              <>
                <Image className="h-4 w-4" />
                Build from Screenshot
              </>
            )}
          </button>
        </form>
      )}

      {success && (
        <div className="mt-3 flex items-center gap-2 rounded border border-emerald-900 bg-emerald-950/50 px-3 py-2">
          <CheckCircle className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
          <p className="font-mono text-xs text-emerald-400">
            Build started! Check the feed for progress.
          </p>
        </div>
      )}
      {error && (
        <p className="mt-3 rounded border border-red-900 bg-red-950/50 px-3 py-2 font-mono text-xs text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
