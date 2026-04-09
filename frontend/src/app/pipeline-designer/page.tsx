"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Save, Play, Settings, GitBranch } from "lucide-react";
import { PipelineDesigner } from "@/components/PipelineDesigner";
import type { PipelineConfig } from "@/lib/pipeline-types";

export default function PipelineDesignerPage() {
  const [saved, setSaved] = useState(false);

  const handleSave = async (pipeline: PipelineConfig) => {
    console.log("Saving pipeline:", pipeline);
    // TODO: Save to backend
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleRun = async (pipeline: PipelineConfig) => {
    console.log("Running pipeline:", pipeline);
    // TODO: Execute pipeline
    alert("Pipeline execution started! Check console for details.");
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 font-mono text-xs text-neutral-600 transition-colors hover:text-neutral-300"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back
          </Link>
          <div>
            <h1 className="text-xl font-bold text-neutral-100 flex items-center gap-2">
              <GitBranch className="h-5 w-5 text-violet-400" />
              Pipeline Designer
            </h1>
            <p className="text-sm text-neutral-500">
              Design custom build pipelines with drag-and-drop nodes
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {saved && (
            <span className="text-xs text-emerald-400 animate-pulse">Saved!</span>
          )}
          <button className="flex items-center gap-2 rounded border border-neutral-800 bg-neutral-900 px-3 py-1.5 text-xs text-neutral-400 hover:text-neutral-300">
            <Settings className="h-3.5 w-3.5" />
            Settings
          </button>
        </div>
      </div>

      {/* Designer */}
      <PipelineDesigner onSave={handleSave} onRun={handleRun} />

      {/* Help text */}
      <div className="mt-4 rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
        <h3 className="mb-2 font-semibold text-sm text-neutral-300">How to use</h3>
        <ul className="space-y-1 text-xs text-neutral-500">
          <li>• <strong>Add nodes</strong> from the left palette by clicking on them</li>
          <li>• <strong>Connect nodes</strong> by dragging from an output port (right side) to an input port (left side)</li>
          <li>• <strong>Configure nodes</strong> by selecting them and editing properties in the right panel</li>
          <li>• <strong>Delete nodes</strong> by selecting them and clicking Delete in the properties panel</li>
          <li>• <strong>Move nodes</strong> by dragging them around the canvas</li>
          <li>• <strong>Zoom</strong> using the +/- buttons in the properties panel header</li>
        </ul>
      </div>
    </div>
  );
}
