"use client";

import { AlertCircle, RefreshCw, X, ExternalLink, HelpCircle } from "lucide-react";
import { useState } from "react";

export interface ErrorInfo {
  message: string;
  code?: string;
  details?: string;
  suggestions?: string[];
  docsUrl?: string;
  retryable?: boolean;
  onRetry?: () => void;
}

interface ErrorDisplayProps {
  error: ErrorInfo | string;
  onDismiss?: () => void;
  onRetry?: () => void;
  variant?: "inline" | "card" | "toast";
  className?: string;
}

const ERROR_CODES: Record<string, { title: string; suggestions: string[] }> = {
  RATE_LIMIT: {
    title: "Rate Limit Exceeded",
    suggestions: [
      "Wait a few minutes before trying again",
      "Consider upgrading your plan for higher limits",
    ],
  },
  VALIDATION_FAILED: {
    title: "Validation Failed",
    suggestions: [
      "Check that your prompt is clear and specific",
      "Try simplifying your request",
      "Ensure any referenced files exist",
    ],
  },
  DEPLOY_FAILED: {
    title: "Deployment Failed",
    suggestions: [
      "Check the build logs for errors",
      "Verify your project dependencies are correct",
      "Try deploying again after fixing issues",
    ],
  },
  TIMEOUT: {
    title: "Request Timed Out",
    suggestions: [
      "The operation took too long",
      "Try again with a simpler request",
      "Check your internet connection",
    ],
  },
  NETWORK_ERROR: {
    title: "Network Error",
    suggestions: [
      "Check your internet connection",
      "Try refreshing the page",
      "The server may be temporarily unavailable",
    ],
  },
  UNAUTHORIZED: {
    title: "Authentication Required",
    suggestions: [
      "Sign in to your account",
      "Your session may have expired",
    ],
  },
};

export function ErrorDisplay({
  error,
  onDismiss,
  onRetry,
  variant = "inline",
  className = "",
}: ErrorDisplayProps) {
  const [showDetails, setShowDetails] = useState(false);

  const errorInfo: ErrorInfo = typeof error === "string"
    ? { message: error, retryable: !!onRetry }
    : error;

  const errorCode = errorInfo.code || inferErrorCode(errorInfo.message);
  const errorMeta = ERROR_CODES[errorCode];

  const suggestions = errorInfo.suggestions || errorMeta?.suggestions || [];
  const title = errorMeta?.title || "Error";

  if (variant === "toast") {
    return (
      <div className={`fixed bottom-4 right-4 z-50 flex items-start gap-3 rounded-lg border border-red-800 bg-red-950/90 p-4 shadow-xl backdrop-blur-sm ${className}`}>
        <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-red-200">{title}</p>
          <p className="mt-1 text-xs text-red-300/80">{errorInfo.message}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="flex items-center gap-1 rounded bg-red-800/50 px-2 py-1 text-xs text-red-200 hover:bg-red-800"
          >
            <RefreshCw className="h-3 w-3" />
            Retry
          </button>
        )}
        {onDismiss && (
          <button onClick={onDismiss} className="text-red-400 hover:text-red-300">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div className={`rounded-lg border border-red-800/50 bg-red-950/30 p-6 ${className}`}>
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-red-800/30 p-2">
            <AlertCircle className="h-6 w-6 text-red-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-red-200">{title}</h3>
            <p className="mt-1 text-sm text-red-300/80">{errorInfo.message}</p>

            {suggestions.length > 0 && (
              <div className="mt-4">
                <button
                  onClick={() => setShowDetails(!showDetails)}
                  className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300"
                >
                  <HelpCircle className="h-3 w-3" />
                  {showDetails ? "Hide suggestions" : "Show suggestions"}
                </button>
                {showDetails && (
                  <ul className="mt-2 space-y-1 pl-4">
                    {suggestions.map((s, i) => (
                      <li key={i} className="text-xs text-red-300/60 list-disc">
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {errorInfo.details && (
              <details className="mt-3">
                <summary className="cursor-pointer text-xs text-red-400 hover:text-red-300">
                  Technical details
                </summary>
                <pre className="mt-2 overflow-x-auto rounded bg-neutral-900 p-2 font-mono text-[10px] text-neutral-400">
                  {errorInfo.details}
                </pre>
              </details>
            )}

            <div className="mt-4 flex items-center gap-2">
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="flex items-center gap-2 rounded bg-red-800 px-3 py-1.5 text-sm font-medium text-red-100 transition-colors hover:bg-red-700"
                >
                  <RefreshCw className="h-4 w-4" />
                  Try Again
                </button>
              )}
              {errorInfo.docsUrl && (
                <a
                  href={errorInfo.docsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300"
                >
                  <ExternalLink className="h-3 w-3" />
                  Learn more
                </a>
              )}
            </div>
          </div>
          {onDismiss && (
            <button onClick={onDismiss} className="text-red-500 hover:text-red-400">
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // Inline variant (default)
  return (
    <div className={`flex items-start gap-2 ${className}`}>
      <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-red-300">{errorInfo.message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-1 flex items-center gap-1 text-xs text-red-400 hover:text-red-300"
          >
            <RefreshCw className="h-3 w-3" />
            Retry
          </button>
        )}
      </div>
      {onDismiss && (
        <button onClick={onDismiss} className="text-red-500 hover:text-red-400">
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

function inferErrorCode(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("rate limit")) return "RATE_LIMIT";
  if (lower.includes("timeout") || lower.includes("timed out")) return "TIMEOUT";
  if (lower.includes("network") || lower.includes("fetch") || lower.includes("connection")) return "NETWORK_ERROR";
  if (lower.includes("unauthorized") || lower.includes("authentication")) return "UNAUTHORIZED";
  if (lower.includes("deploy")) return "DEPLOY_FAILED";
  if (lower.includes("validation") || lower.includes("invalid")) return "VALIDATION_FAILED";
  return "";
}
