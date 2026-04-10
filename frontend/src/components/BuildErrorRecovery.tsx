"use client";

import { AlertTriangle, RefreshCw, Copy, Check, ArrowRight, Trash2 } from "lucide-react";
import { useState, useMemo } from "react";
import Link from "next/link";
import { formatCheckpointStage, parseBuildFailedCheckpoint } from "@/lib/buildCheckpoint";
import { ErrorDisplay } from "./ErrorDisplay";

interface BuildErrorRecoveryProps {
  buildId: string;
  errorMessage?: string;
  errorDetails?: string;
  prompt?: string;
  onRetry?: () => void;
  onDelete?: () => void;
}

export function BuildErrorRecovery({
  buildId,
  errorMessage,
  errorDetails,
  prompt,
  onRetry,
  onDelete,
}: BuildErrorRecoveryProps) {
  const [copied, setCopied] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const checkpoint = useMemo(
    () => parseBuildFailedCheckpoint(errorDetails),
    [errorDetails]
  );

  const handleCopyPrompt = () => {
    if (prompt) {
      navigator.clipboard.writeText(prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRetry = async () => {
    if (!onRetry) return;
    setRetrying(true);
    try {
      await onRetry();
    } finally {
      setRetrying(false);
    }
  };

  // Parse common error patterns to provide better suggestions
  const getErrorSuggestions = (): string[] => {
    const suggestions: string[] = [];
    const msg = (errorMessage || "").toLowerCase();
    const details = (errorDetails || "").toLowerCase();

    if (msg.includes("api key") || details.includes("api key")) {
      suggestions.push("Check that your API keys are configured correctly");
      suggestions.push("Verify the API key has the required permissions");
    }
    if (msg.includes("rate limit") || details.includes("rate limit")) {
      suggestions.push("Wait a few minutes before retrying");
      suggestions.push("Consider reducing the complexity of your request");
    }
    if (msg.includes("timeout") || details.includes("timeout")) {
      suggestions.push("The build took too long - try a simpler prompt");
      suggestions.push("Check the server status and try again");
    }
    if (msg.includes("syntax") || details.includes("syntax")) {
      suggestions.push("There was a code generation issue - try rephrasing your prompt");
    }
    if (msg.includes("dependency") || details.includes("import") || details.includes("module")) {
      suggestions.push("A dependency error occurred - the AI will try to fix it on retry");
    }

    if (suggestions.length === 0) {
      suggestions.push("Try retrying the build");
      suggestions.push("If the issue persists, try a different prompt");
    }

    return suggestions;
  };

  return (
    <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-6">
      <div className="flex items-start gap-4">
        <div className="rounded-full bg-red-800/30 p-3 shrink-0">
          <AlertTriangle className="h-6 w-6 text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-red-200">Build Failed</h3>
          <p className="mt-1 text-sm text-red-300/70">
            Something went wrong during the build process. Here&apos;s what you can do:
          </p>
          {checkpoint && (
            <p className="mt-3 rounded-md border border-amber-800/40 bg-amber-950/25 px-3 py-2 text-sm text-amber-100/90">
              <span className="font-semibold text-amber-200">Last failed checkpoint:</span>{" "}
              {formatCheckpointStage(checkpoint.stage)}
              <span className="mt-1 block text-xs font-normal text-amber-200/70">
                Retry resumes from this step and reuses saved artifacts (manifest, files, or HTML)
                when the server can, instead of starting from zero.
              </span>
            </p>
          )}

          {/* Error details */}
          {(errorMessage || errorDetails) && (
            <div className="mt-4">
              <ErrorDisplay
                error={{
                  message: errorMessage || "An unexpected error occurred",
                  details: errorDetails,
                  suggestions: getErrorSuggestions(),
                  retryable: !!onRetry,
                }}
                variant="inline"
              />
            </div>
          )}

          {/* Actions */}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            {onRetry && (
              <button
                onClick={handleRetry}
                disabled={retrying}
                className="flex items-center gap-2 rounded bg-red-800 px-4 py-2 font-medium text-sm text-red-100 transition-colors hover:bg-red-700 disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${retrying ? "animate-spin" : ""}`} />
                {retrying ? "Retrying…" : checkpoint ? "Retry from checkpoint" : "Retry build"}
              </button>
            )}

            {prompt && (
              <button
                onClick={handleCopyPrompt}
                className="flex items-center gap-2 rounded border border-neutral-700 bg-neutral-900 px-4 py-2 font-medium text-sm text-neutral-300 transition-colors hover:bg-neutral-800"
              >
                {copied ? (
                  <>
                    <Check className="h-4 w-4 text-emerald-400" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    Copy Prompt
                  </>
                )}
              </button>
            )}

            <Link
              href="/"
              className="flex items-center gap-2 rounded border border-neutral-700 bg-neutral-900 px-4 py-2 font-medium text-sm text-neutral-300 transition-colors hover:bg-neutral-800"
            >
              Start New Build
              <ArrowRight className="h-4 w-4" />
            </Link>

            {onDelete && (
              <button
                onClick={onDelete}
                className="flex items-center gap-2 rounded border border-neutral-800 px-4 py-2 font-medium text-sm text-neutral-500 transition-colors hover:border-red-800 hover:text-red-400"
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </button>
            )}
          </div>

          {/* Original prompt */}
          {prompt && (
            <details className="mt-4">
              <summary className="cursor-pointer text-xs text-neutral-500 hover:text-neutral-400">
                View original prompt
              </summary>
              <div className="mt-2 rounded border border-neutral-800 bg-neutral-900 p-3">
                <p className="font-mono text-xs text-neutral-400">{prompt}</p>
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
