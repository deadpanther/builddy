/**
 * Matches backend `retry_build` parsing: errors are stored as `[stage] message`
 * (see agent/pipeline.py _update_build / routers/builds retry_build).
 */
export function parseBuildFailedCheckpoint(
  error: string | null | undefined
): { stage: string; message: string } | null {
  if (!error?.trim()) return null;
  const m = error.trim().match(/^\[([^\]]+)\]\s*([\s\S]*)$/);
  if (!m) return null;
  const stage = m[1].trim();
  if (!stage) return null;
  return { stage, message: m[2].trim() };
}

const STAGE_LABELS: Record<string, string> = {
  pending: "Queued",
  planning: "Planning",
  coding: "Code generation",
  reviewing: "Review",
  deploying: "Deploy",
};

export function formatCheckpointStage(stage: string): string {
  const key = stage.toLowerCase();
  return STAGE_LABELS[key] ?? stage.replace(/_/g, " ");
}
