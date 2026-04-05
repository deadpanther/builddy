"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface CodePreviewProps {
  code: string;
  language?: string;
  className?: string;
}

export function CodePreview({ code, language = "html", className }: CodePreviewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn("rounded-lg border border-neutral-800 bg-neutral-950 overflow-hidden", className)}>
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-2">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="h-3 w-3 rounded-full bg-red-500/70" />
            <span className="h-3 w-3 rounded-full bg-yellow-500/70" />
            <span className="h-3 w-3 rounded-full bg-green-500/70" />
          </div>
          <span className="font-mono text-xs text-neutral-600">{language}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded border border-neutral-800 bg-neutral-900 px-2 py-1 font-mono text-[10px] text-neutral-500 transition-colors hover:border-neutral-700 hover:text-neutral-300"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-400" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Code content */}
      <pre className="max-h-[500px] overflow-auto p-4 font-mono text-xs leading-relaxed text-neutral-300">
        <code>{code}</code>
      </pre>
    </div>
  );
}
