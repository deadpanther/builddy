"use client";

import { useState } from "react";
import { ExternalLink, RefreshCw, Maximize2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface AppPreviewProps {
  url: string;
  className?: string;
}

export function AppPreview({ url, className }: AppPreviewProps) {
  const [key, setKey] = useState(0);

  return (
    <div className={cn("rounded-lg border border-neutral-800 bg-neutral-950 overflow-hidden", className)}>
      {/* Browser chrome */}
      <div className="flex items-center gap-2 border-b border-neutral-800 bg-neutral-900 px-3 py-2">
        <div className="flex gap-1.5">
          <span className="h-3 w-3 rounded-full bg-red-500/70" />
          <span className="h-3 w-3 rounded-full bg-yellow-500/70" />
          <span className="h-3 w-3 rounded-full bg-green-500/70" />
        </div>

        {/* URL bar */}
        <div className="flex flex-1 items-center gap-2 rounded border border-neutral-800 bg-neutral-950 px-3 py-1">
          <span className="font-mono text-[10px] text-neutral-500 truncate">{url}</span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setKey((k) => k + 1)}
            title="Reload"
            className="rounded p-1 text-neutral-500 transition-colors hover:text-neutral-300"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            title="Open in new tab"
            className="rounded p-1 text-neutral-500 transition-colors hover:text-neutral-300"
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      {/* iframe */}
      <iframe
        key={key}
        src={url}
        className="h-[500px] w-full border-0"
        title="App Preview"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
      />
    </div>
  );
}
