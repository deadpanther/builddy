"use client";

import { useState, type FormEvent } from "react";
import { Wand2, Send, Loader2 } from "lucide-react";
import { modifyBuild } from "@/lib/api";
import type { Build } from "@/lib/types";

interface ModifyFormProps {
  build: Build;
  onModify: (newBuildId: string) => void;
}

export function ModifyForm({ build, onModify }: ModifyFormProps) {
  const [text, setText] = useState("");
  const [modifying, setModifying] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    setModifying(true);
    setError("");
    try {
      const newBuild = await modifyBuild(build.id, text.trim());
      onModify(newBuild.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to modify");
    } finally {
      setModifying(false);
    }
  };

  if (build.status !== "deployed") return null;

  return (
    <form onSubmit={handleSubmit} className="mt-4">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Wand2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-600" />
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Add dark mode, fix the button, etc."
            className="w-full rounded border border-neutral-800 bg-neutral-950 py-2.5 pl-10 pr-4 font-mono text-sm text-neutral-300 placeholder:text-neutral-600 focus:border-violet-700 focus:outline-none"
            disabled={modifying}
          />
        </div>
        <button
          type="submit"
          disabled={modifying || !text.trim()}
          className="flex items-center gap-2 rounded bg-violet-800 px-4 py-2 font-semibold text-sm text-violet-100 transition-colors hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {modifying ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          Modify
        </button>
      </div>
      {error && <p className="mt-2 font-mono text-xs text-red-400">{error}</p>}
    </form>
  );
}
