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

function buildAdvancedExtras(
  webhookUrl: string,
  acceptancePaths: string,
  extraJson: string,
  setError: (s: string) => void
): { build_options?: Record<string, unknown>; webhook_url?: string } | null {
  const paths = acceptancePaths
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const opts: Record<string, unknown> = {};
  if (paths.length) opts.acceptance_paths = paths;
  if (extraJson.trim()) {
    try {
      Object.assign(opts, JSON.parse(extraJson) as Record<string, unknown>);
    } catch {
      setError("Advanced: invalid JSON object");
      return null;
    }
  }
  return {
    build_options: Object.keys(opts).length ? opts : undefined,
    webhook_url: webhookUrl.trim() || undefined,
  };
}

export function SubmitBuild({ onBuildCreated }: SubmitBuildProps) {
  const [mode, setMode] = useState<"text" | "screenshot">("text");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [images, setImages] = useState<{ base64: string; preview: string }[]>([]);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [acceptancePaths, setAcceptancePaths] = useState("");
  const [extraJson, setExtraJson] = useState("");

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
      const adv = buildAdvancedExtras(webhookUrl, acceptancePaths, extraJson, setError);
      if (adv === null) {
        setLoading(false);
        return;
      }
      const build = await createBuild(trimmed, adv);
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
      const adv = buildAdvancedExtras(webhookUrl, acceptancePaths, extraJson, setError);
      if (adv === null) {
        setLoading(false);
        return;
      }
      const b64List = images.map((img) => img.base64);
      const imagePayload = b64List.length === 1 ? b64List[0] : b64List;
      const build = await createBuildFromImage(imagePayload, prompt, adv);
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
    <div className="glass-panel p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-500/15">
          <Sparkles className="h-4 w-4 text-brand-400" />
        </div>
        <h2 className="text-sm font-semibold text-white">Build an App</h2>
      </div>

      {/* Mode tabs */}
      <div className="mb-4 flex gap-1 rounded-lg bg-surface-100 p-1">
        <button
          type="button"
          onClick={() => setMode("text")}
          className={cn(
            "flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition-all",
            mode === "text"
              ? "bg-brand-500/20 text-brand-300 shadow-inner-glow"
              : "text-zinc-500 hover:text-zinc-300"
          )}
        >
          <Type className="h-3 w-3" />
          Describe
        </button>
        <button
          type="button"
          onClick={() => setMode("screenshot")}
          className={cn(
            "flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition-all",
            mode === "screenshot"
              ? "bg-brand-500/20 text-brand-300 shadow-inner-glow"
              : "text-zinc-500 hover:text-zinc-300"
          )}
        >
          <Image className="h-3 w-3" />
          Screenshot
        </button>
      </div>

      <button
        type="button"
        onClick={() => setShowAdvanced((v) => !v)}
        className="mb-3 w-full rounded-lg border border-stroke bg-surface-100 py-2 font-mono text-[10px] text-zinc-500 hover:text-zinc-300"
      >
        {showAdvanced ? "Hide advanced" : "Advanced: webhooks & acceptance URLs"}
      </button>

      {showAdvanced && (
        <div className="mb-4 space-y-2 rounded-lg border border-stroke bg-surface-100/50 p-3">
          <div>
            <label className="mb-1 block font-mono text-[10px] text-zinc-500">Webhook URL (optional)</label>
            <input
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://example.com/hooks/builddy"
              className="w-full rounded border border-stroke bg-surface px-2 py-1.5 font-mono text-xs text-white"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-[10px] text-zinc-500">
              Paths that must return 200 (comma-separated, after deploy)
            </label>
            <input
              value={acceptancePaths}
              onChange={(e) => setAcceptancePaths(e.target.value)}
              placeholder="/, /api/health"
              className="w-full rounded border border-stroke bg-surface px-2 py-1.5 font-mono text-xs text-white"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-[10px] text-zinc-500">Extra build_options JSON object (optional)</label>
            <textarea
              value={extraJson}
              onChange={(e) => setExtraJson(e.target.value)}
              placeholder='{"pwa": true}'
              rows={2}
              className="w-full rounded border border-stroke bg-surface px-2 py-1.5 font-mono text-xs text-white"
            />
          </div>
        </div>
      )}

      {mode === "text" ? (
        /* ── Text mode ────────────────────────────── */
        <form onSubmit={handleSubmitText} className="space-y-3">
          <div>
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-wider text-zinc-500">
              Describe your app
            </label>
            <textarea
              value={prompt}
              onChange={(e) => { setPrompt(e.target.value); setError(""); setSuccess(""); }}
              placeholder="Build me a Pomodoro timer with dark mode..."
              rows={4}
              disabled={loading}
              className={cn(
                "w-full resize-none rounded-lg border bg-surface px-3.5 py-2.5 font-mono text-sm text-white placeholder:text-zinc-600 outline-none transition-all",
                "border-stroke focus:border-brand-500/50 focus:ring-2 focus:ring-brand-500/20",
                loading && "opacity-50 cursor-not-allowed"
              )}
            />
          </div>

          <div>
            <p className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-zinc-600">
              Quick examples
            </p>
            <div className="flex flex-wrap gap-1.5">
              {EXAMPLE_PROMPTS.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  onClick={() => setPrompt(`Build me ${ex}`)}
                  className="rounded-md border border-stroke bg-surface-100 px-2.5 py-1 font-mono text-[10px] text-zinc-500 transition-all hover:border-stroke-hover hover:text-white hover:bg-surface-200"
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
              "flex w-full items-center justify-center gap-2 rounded-lg border px-4 py-2.5 font-semibold text-sm transition-all",
              "bg-brand-500/20 border-brand-500/30 text-brand-300 hover:bg-brand-500/30",
              "disabled:opacity-30 disabled:cursor-not-allowed"
            )}
          >
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-300 border-t-transparent" />
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
        /* ── Screenshot mode ──────────────────────── */
        <form onSubmit={handleSubmitScreenshot} className="space-y-3">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            {images.length === 0 ? (
              <div
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-8 transition-all",
                  dragging
                    ? "border-brand-400 bg-brand-500/10"
                    : "border-stroke bg-surface hover:border-stroke-hover"
                )}
              >
                <Upload className="mb-2 h-8 w-8 text-zinc-600" />
                <p className="text-sm text-zinc-400">
                  Drop screenshot(s) or mockup(s) here
                </p>
                <p className="mt-1 font-mono text-[10px] text-zinc-600">
                  PNG, JPG up to 5MB each
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
                        className="h-24 w-auto rounded-lg border border-stroke object-contain"
                      />
                      <button
                        type="button"
                        onClick={() => setImages((prev) => prev.filter((_, idx) => idx !== i))}
                        className="absolute -right-1 -top-1 rounded-full bg-danger/80 p-0.5 text-white opacity-0 transition-opacity group-hover:opacity-100"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex h-24 w-20 items-center justify-center rounded-lg border-2 border-dashed border-stroke text-zinc-600 transition-all hover:border-stroke-hover hover:text-zinc-400"
                  >
                    <span className="text-2xl">+</span>
                  </button>
                </div>
                <p className="font-mono text-[10px] text-zinc-600">
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
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-wider text-zinc-500">
              Additional instructions (optional)
            </label>
            <input
              type="text"
              value={prompt}
              onChange={(e) => { setPrompt(e.target.value); setError(""); }}
              placeholder="Make all buttons functional, add dark mode..."
              disabled={loading}
              className={cn(
                "w-full rounded-lg border bg-surface px-3.5 py-2.5 font-mono text-sm text-white placeholder:text-zinc-600 outline-none transition-all",
                "border-stroke focus:border-brand-500/50 focus:ring-2 focus:ring-brand-500/20",
                loading && "opacity-50 cursor-not-allowed"
              )}
            />
          </div>

          <button
            type="submit"
            disabled={loading || images.length === 0}
            className={cn(
              "flex w-full items-center justify-center gap-2 rounded-lg border px-4 py-2.5 font-semibold text-sm transition-all",
              "bg-brand-500/20 border-brand-500/30 text-brand-300 hover:bg-brand-500/30",
              "disabled:opacity-30 disabled:cursor-not-allowed"
            )}
          >
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-300 border-t-transparent" />
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
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-success-border bg-success-dim px-3 py-2">
          <CheckCircle className="h-3.5 w-3.5 text-success shrink-0" />
          <p className="font-mono text-xs text-success">
            Build started! Check the feed for progress.
          </p>
        </div>
      )}
      {error && (
        <p className="mt-3 rounded-lg border border-danger-border bg-danger-dim px-3 py-2 font-mono text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
