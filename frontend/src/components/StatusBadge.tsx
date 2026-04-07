import { cn } from "@/lib/utils";
import type { BuildStatus } from "@/lib/types";

const STATUS_CONFIG: Record<BuildStatus, { label: string; className: string; dot: string }> = {
  pending: {
    label: "Pending",
    className: "bg-surface-100 text-zinc-400 border-stroke",
    dot: "bg-zinc-500",
  },
  planning: {
    label: "Planning",
    className: "bg-info-dim text-info border-info-border",
    dot: "bg-info",
  },
  coding: {
    label: "Coding",
    className: "bg-warning-dim text-warning border-warning-border",
    dot: "bg-warning animate-pulse",
  },
  reviewing: {
    label: "Reviewing",
    className: "bg-brand-500/15 text-brand-300 border-brand-500/25",
    dot: "bg-brand-400 animate-pulse",
  },
  deploying: {
    label: "Deploying",
    className: "bg-orange-500/15 text-orange-400 border-orange-500/25",
    dot: "bg-orange-400 animate-pulse",
  },
  deployed: {
    label: "Deployed",
    className: "bg-success-dim text-success border-success-border",
    dot: "bg-success",
  },
  failed: {
    label: "Failed",
    className: "bg-danger-dim text-danger border-danger-border",
    dot: "bg-danger",
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
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider",
        config.className,
        className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
      {config.label}
    </span>
  );
}
