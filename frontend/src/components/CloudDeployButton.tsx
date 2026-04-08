"use client";

import { useState } from "react";
import { Cloud, Rocket, Globe, Terminal, ExternalLink, X, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { cloudDeploy, getDeployStatus } from "@/lib/api";
import type { CloudDeployInstructions } from "@/lib/api";
import type { Build } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CloudDeployButtonProps {
  build: Build;
  onBuildUpdate: (build: Build) => void;
}

export function CloudDeployButton({ build, onBuildUpdate }: CloudDeployButtonProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [error, setError] = useState("");
  const [instructions, setInstructions] = useState<CloudDeployInstructions | null>(null);

  const handleDeploy = async (provider: "railway" | "render") => {
    setDeploying(true);
    setError("");
    setInstructions(null);

    try {
      const updated = await cloudDeploy(build.id, provider);
      onBuildUpdate(updated);
      // Check if we got manual instructions
      if (updated.deploy_status === "manual" || updated.deploy_status === "ready") {
        const statusResult = await getDeployStatus(build.id);
        if (statusResult.instructions) {
          setInstructions(statusResult.instructions);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to deploy");
    } finally {
      setDeploying(false);
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
        className={cn(
          "flex items-center gap-2 rounded border px-4 py-2 font-semibold text-sm transition-colors",
          build.deploy_status === "live"
            ? "border-emerald-700 bg-emerald-900/40 text-emerald-300 hover:bg-emerald-900/70"
            : build.deploy_status === "deploying"
              ? "border-amber-700 bg-amber-900/40 text-amber-300 hover:bg-amber-900/70"
              : "border-orange-700 bg-orange-900/40 text-orange-300 hover:bg-orange-900/70"
        )}
      >
        {build.deploy_status === "deploying" ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : build.deploy_status === "live" ? (
          <CheckCircle className="h-4 w-4" />
        ) : (
          <Cloud className="h-4 w-4" />
        )}
        {build.deploy_status === "live"
          ? "Deployed"
          : build.deploy_status === "deploying"
            ? "Deploying..."
            : "Deploy to Cloud"}
      </button>
      {showDropdown && (
        <div className="absolute right-0 top-full z-10 mt-2 w-96 rounded-lg border border-orange-900/50 bg-neutral-900 p-4 shadow-xl">
          <div className="mb-3 flex items-center justify-between">
            <span className="flex items-center gap-2 font-semibold text-sm text-orange-300">
              <Cloud className="h-3.5 w-3.5" />
              Deploy to Cloud
            </span>
            <button
              type="button"
              onClick={() => {
                setShowDropdown(false);
                setError("");
                setInstructions(null);
              }}
              className="text-neutral-600 hover:text-neutral-400"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* External URL if already deployed */}
          {build.deploy_external_url && (
            <a
              href={build.deploy_external_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mb-3 flex items-center gap-2 rounded border border-emerald-800 bg-emerald-950/30 px-3 py-2 font-mono text-xs text-emerald-400 hover:bg-emerald-950/50"
            >
              <Globe className="h-3.5 w-3.5" />
              {build.deploy_external_url}
            </a>
          )}

          {/* Provider buttons */}
          {!instructions && (
            <div className="space-y-2">
              <button
                onClick={() => handleDeploy("railway")}
                disabled={deploying}
                className="flex w-full items-center gap-3 rounded border border-neutral-800 bg-neutral-950 px-3 py-3 text-left transition-colors hover:border-neutral-700 hover:bg-neutral-900 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Rocket className="h-5 w-5 text-violet-400 shrink-0" />
                <div className="min-w-0">
                  <span className="block text-sm font-medium text-neutral-200">Railway</span>
                  <span className="block font-mono text-[10px] text-neutral-600">Instant deploy with auto-scaling</span>
                </div>
                {deploying && <Loader2 className="h-4 w-4 animate-spin text-neutral-500 ml-auto" />}
              </button>
              <button
                onClick={() => handleDeploy("render")}
                disabled={deploying}
                className="flex w-full items-center gap-3 rounded border border-neutral-800 bg-neutral-950 px-3 py-3 text-left transition-colors hover:border-neutral-700 hover:bg-neutral-900 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Globe className="h-5 w-5 text-teal-400 shrink-0" />
                <div className="min-w-0">
                  <span className="block text-sm font-medium text-neutral-200">Render</span>
                  <span className="block font-mono text-[10px] text-neutral-600">Static and full-stack hosting</span>
                </div>
                {deploying && <Loader2 className="h-4 w-4 animate-spin text-neutral-500 ml-auto" />}
              </button>
            </div>
          )}

          {/* Manual instructions */}
          {instructions && (
            <div className="space-y-3">
              <p className="text-xs text-neutral-400">{instructions.message}</p>
              {instructions.repo_url && (
                <a
                  href={instructions.repo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 rounded border border-neutral-800 bg-neutral-950 px-3 py-2 font-mono text-xs text-sky-400 hover:bg-neutral-900"
                >
                  <ExternalLink className="h-3 w-3" />
                  {instructions.repo_url}
                </a>
              )}
              {instructions.steps && (
                <ol className="space-y-1 pl-4 list-decimal">
                  {instructions.steps.map((step, i) => (
                    <li key={i} className="font-mono text-[11px] text-neutral-500">{step}</li>
                  ))}
                </ol>
              )}
              {instructions.options && (
                <div className="space-y-3">
                  {instructions.options.map((opt) => (
                    <div key={opt.provider} className="rounded border border-neutral-800 bg-neutral-950 p-3">
                      <span className="mb-1.5 block text-xs font-medium text-neutral-300">{opt.name}</span>
                      <ol className="space-y-0.5 pl-4 list-decimal">
                        {opt.steps.map((step, i) => (
                          <li key={i} className="font-mono text-[10px] text-neutral-600">{step}</li>
                        ))}
                      </ol>
                      {opt.one_liner && (
                        <div className="mt-2 flex items-start gap-2 rounded bg-neutral-900 p-2">
                          <Terminal className="h-3 w-3 text-neutral-600 mt-0.5 shrink-0" />
                          <code className="break-all font-mono text-[10px] text-neutral-500">{opt.one_liner}</code>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {instructions.docs_url && (
                <a
                  href={instructions.docs_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-mono text-[10px] text-sky-500 hover:text-sky-400"
                >
                  <ExternalLink className="h-2.5 w-2.5" />
                  Documentation
                </a>
              )}
            </div>
          )}

          {error && (
            <div className="mt-2 flex items-start gap-2">
              <AlertCircle className="h-3.5 w-3.5 text-red-400 mt-0.5 shrink-0" />
              <p className="font-mono text-xs text-red-400">{error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
