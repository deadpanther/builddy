import { cn } from "@/lib/utils";
import type { BuildStatus } from "@/lib/types";
import { CheckCircle, Circle, AlertCircle, Loader, Terminal, Brain, Search, ImageIcon } from "lucide-react";

const PIPELINE_STEPS: { key: string; title: string; description: string }[] = [
  { key: "planning", title: "Planning", description: "Analyzing request and planning architecture with GLM 5.1" },
  { key: "coding", title: "Coding", description: "Generating complete HTML/CSS/JS with thinking mode" },
  { key: "reviewing", title: "Reviewing", description: "Self-reviewing code for bugs and completeness" },
  { key: "deploying", title: "Deploying", description: "Deploying to static hosting and generating URL" },
];

const STATUS_ORDER: BuildStatus[] = [
  "pending", "planning", "coding", "reviewing", "deploying", "deployed", "failed",
];

function getStepStatus(
  stepKey: string,
  buildStatus: BuildStatus,
  failedAtStatus?: string | null
): "pending" | "active" | "done" | "failed" {
  if (buildStatus === "failed") {
    const stepIdx = PIPELINE_STEPS.findIndex((s) => s.key === stepKey);
    if (failedAtStatus) {
      const failedIdx = PIPELINE_STEPS.findIndex((s) => s.key === failedAtStatus);
      if (failedIdx !== -1) {
        if (stepIdx < failedIdx) return "done";
        if (stepIdx === failedIdx) return "failed";
        return "pending";
      }
    }
    return stepIdx === 0 ? "failed" : "pending";
  }
  if (buildStatus === "deployed") return "done";

  const buildIdx = STATUS_ORDER.indexOf(buildStatus);
  const stepIdx = PIPELINE_STEPS.findIndex((s) => s.key === stepKey);

  if (stepIdx < buildIdx - 1) return "done";
  if (stepIdx === buildIdx - 1) return "active";
  return "pending";
}

/** Detect special step prefixes for badge rendering */
function getStepBadge(step: string): { icon: typeof Brain; label: string; color: string } | null {
  if (step.startsWith("[thinking]")) return { icon: Brain, label: "Thinking", color: "text-purple-400 bg-purple-950/50 border-purple-800" };
  if (step.startsWith("[research]")) return { icon: Search, label: "Web Search", color: "text-blue-400 bg-blue-950/50 border-blue-800" };
  if (step.startsWith("[image]")) return { icon: ImageIcon, label: "CogView-4", color: "text-amber-400 bg-amber-950/50 border-amber-800" };
  return null;
}

interface AgentStepsProps {
  buildStatus: BuildStatus;
  failedAtStatus?: string | null;
  rawSteps?: string[];
}

export function AgentSteps({ buildStatus, failedAtStatus, rawSteps }: AgentStepsProps) {
  return (
    <div className="space-y-0">
      {/* Visual pipeline */}
      {PIPELINE_STEPS.map((pipelineStep, i) => {
        const status = getStepStatus(pipelineStep.key, buildStatus, failedAtStatus);

        return (
          <div key={pipelineStep.key} className="flex gap-4">
            <div className="flex flex-col items-center">
              <StepIcon status={status} />
              {i < PIPELINE_STEPS.length - 1 && (
                <div
                  className={cn(
                    "mt-1 w-0.5 flex-1",
                    status === "done" ? "bg-emerald-700" : "bg-neutral-800"
                  )}
                  style={{ minHeight: "28px" }}
                />
              )}
            </div>

            <div className="pb-6 flex-1 min-w-0">
              <div
                className={cn(
                  "font-medium text-sm",
                  status === "done" && "text-emerald-400",
                  status === "active" && "text-amber-300",
                  status === "failed" && "text-red-400",
                  status === "pending" && "text-neutral-600"
                )}
              >
                {pipelineStep.title}
                {status === "active" && (
                  <span className="ml-2 font-mono text-[10px] uppercase tracking-wider text-amber-500 animate-pulse">
                    in progress
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-xs text-neutral-600">
                {pipelineStep.description}
              </p>
            </div>
          </div>
        );
      })}

      {/* Raw pipeline log with badges */}
      {rawSteps && rawSteps.length > 0 && (
        <div className="mt-4 border-t border-neutral-800 pt-4">
          <div className="mb-2 flex items-center gap-1.5">
            <Terminal className="h-3 w-3 text-neutral-600" />
            <span className="font-mono text-[10px] uppercase tracking-wider text-neutral-600">
              Pipeline Log
            </span>
          </div>
          <div className="max-h-64 overflow-y-auto rounded border border-neutral-800 bg-neutral-950 p-3 space-y-1">
            {rawSteps.map((step, i) => {
              const badge = getStepBadge(step);
              const displayText = step.replace(/^\[(thinking|research|image)\]\s*/, "");

              return (
                <div key={i} className="flex gap-2 text-xs leading-relaxed">
                  <span className="shrink-0 font-mono text-neutral-700 select-none">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {badge ? (
                    <span className="flex items-center gap-1.5 flex-wrap">
                      <span className={cn("inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[10px]", badge.color)}>
                        <badge.icon className="h-2.5 w-2.5" />
                        {badge.label}
                      </span>
                      <span className="font-mono text-neutral-500">{displayText}</span>
                    </span>
                  ) : (
                    <span className={cn(
                      "font-mono",
                      step.toLowerCase().includes("failed") ? "text-red-400" : "text-neutral-500"
                    )}>
                      {step}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function StepIcon({ status }: { status: "pending" | "active" | "done" | "failed" }) {
  const base = "h-5 w-5 shrink-0 mt-0.5";
  if (status === "done") return <CheckCircle className={cn(base, "text-emerald-500")} />;
  if (status === "active") return <Loader className={cn(base, "text-amber-400 animate-spin")} />;
  if (status === "failed") return <AlertCircle className={cn(base, "text-red-500")} />;
  return <Circle className={cn(base, "text-neutral-700")} />;
}
