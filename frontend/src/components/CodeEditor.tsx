"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Copy, Check, Save, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface CodeEditorProps {
  code: string;
  language?: string;
  fileName?: string;
  className?: string;
  readOnly?: boolean;
  onSave?: (content: string) => Promise<void>;
}

export function CodeEditor({
  code,
  language = "html",
  fileName,
  className,
  readOnly = false,
  onSave,
}: CodeEditorProps) {
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [editedCode, setEditedCode] = useState(code);
  const [hasChanges, setHasChanges] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sync when the external code prop changes (e.g. switching files)
  useEffect(() => {
    setEditedCode(code);
    setHasChanges(false);
  }, [code]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(editedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSave = useCallback(async () => {
    if (!onSave || saving || !hasChanges) return;
    setSaving(true);
    try {
      await onSave(editedCode);
      setHasChanges(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // error handled by parent
    } finally {
      setSaving(false);
    }
  }, [onSave, editedCode, saving, hasChanges]);

  // Ctrl/Cmd+S to save
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    },
    [handleSave],
  );

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newVal = e.target.value;
    setEditedCode(newVal);
    setHasChanges(newVal !== code);
  };

  // Sync scroll and handle tab key
  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    handleKeyDown(e);
    if (e.key === "Tab") {
      e.preventDefault();
      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newValue = editedCode.substring(0, start) + "  " + editedCode.substring(end);
      setEditedCode(newValue);
      setHasChanges(newValue !== code);
      // Restore cursor position after React re-render
      requestAnimationFrame(() => {
        textarea.selectionStart = start + 2;
        textarea.selectionEnd = start + 2;
      });
    }
  };

  return (
    <div
      className={cn(
        "rounded-lg border border-neutral-800 bg-neutral-950 overflow-hidden min-w-0 max-w-full",
        hasChanges && "border-amber-800/60",
        className,
      )}
    >
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-2">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="h-3 w-3 rounded-full bg-red-500/70" />
            <span className="h-3 w-3 rounded-full bg-yellow-500/70" />
            <span className="h-3 w-3 rounded-full bg-green-500/70" />
          </div>
          <span className="font-mono text-xs text-neutral-600">
            {fileName || language}
          </span>
          {hasChanges && (
            <span className="font-mono text-[10px] text-amber-500">unsaved</span>
          )}
          {saved && (
            <span className="font-mono text-[10px] text-emerald-500">saved</span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {!readOnly && onSave && (
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className={cn(
                "flex items-center gap-1.5 rounded border px-2 py-1 font-mono text-[10px] transition-colors",
                hasChanges
                  ? "border-amber-700 bg-amber-900/40 text-amber-300 hover:bg-amber-900/60"
                  : "border-neutral-800 bg-neutral-900 text-neutral-600 cursor-not-allowed",
              )}
            >
              {saving ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Save className="h-3 w-3" />
              )}
              {saving ? "Saving..." : "Save"}
              <kbd className="ml-1 text-[9px] opacity-60">&#8984;S</kbd>
            </button>
          )}
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
      </div>

      {/* Code content */}
      {readOnly ? (
        <pre className="max-h-[500px] overflow-auto p-4 font-mono text-xs leading-relaxed text-neutral-300 whitespace-pre-wrap break-all">
          <code>{editedCode}</code>
        </pre>
      ) : (
        <div className="relative overflow-hidden">
          {/* Line numbers gutter */}
          <div className="pointer-events-none absolute left-0 top-0 h-full w-10 border-r border-neutral-900 bg-neutral-950 z-10">
            <pre className="overflow-hidden p-4 pr-2 font-mono text-[10px] leading-relaxed text-right text-neutral-700">
              {editedCode.split("\n").map((_, i) => (
                <div key={i}>{i + 1}</div>
              ))}
            </pre>
          </div>
          <textarea
            ref={textareaRef}
            value={editedCode}
            onChange={handleChange}
            onKeyDown={handleTextareaKeyDown}
            spellCheck={false}
            className="h-[500px] w-full resize-none overflow-auto bg-transparent p-4 pl-12 font-mono text-xs leading-relaxed text-neutral-300 outline-none break-all"
            style={{ wordBreak: "break-all", overflowWrap: "anywhere" }}
          />
        </div>
      )}
    </div>
  );
}
