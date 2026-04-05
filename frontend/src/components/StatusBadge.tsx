import { cn } from "@/lib/utils";
import type { BuildStatus } from "@/lib/types";

const STATUS_CONFIG: Record<BuildStatus, { label: string; className: string; dot: string }> = {
  pending: {
    label: "Pending",
    className: "bg-neutral-900 text-neutral-400 border-neutral-700",
    dot: "bg-neutral-500",
  },
  planning: {
    label: "Planning",
    className: "bg-blue-950 text-blue-300 border-blue-800",
    dot: "bg-blue-400",
  },
  coding: {
    label: "Coding",
    className: "bg-amber-950 text-amber-300 border-amber-800",
    dot: "bg-amber-400 animate-pulse",
  },
  reviewing: {
    label: "Reviewing",
    className: "bg-purple-950 text-purple-300 border-purple-800",
    dot: "bg-purple-400 animate-pulse",
  },
  deploying: {
    label: "Deploying",
    className: "bg-orange-950 text-orange-300 border-orange-800",
    dot: "bg-orange-400 animate-pulse",
  },
  deployed: {
    label: "Deployed",
    className: "bg-emerald-950 text-emerald-300 border-emerald-800",
    dot: "bg-emerald-400",
  },
  failed: {
    label: "Failed",
    className: "bg-red-950 text-red-300 border-red-800",
    dot: "bg-red-400",
  },
};

interface StatusBadgeProps {
  status: BuildStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider",
        config.className,
        className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
      {config.label}
    </span>
  );
}
