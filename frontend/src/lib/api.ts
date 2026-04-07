import type { Build, GalleryApp, AutopsySummary, AutopsyReport, Certificate, EvidenceEntry, FileManifestEntry, TechStack, ComplexityTier, VersionEntry, RevivalPlan, RevivalFeature } from "./types";

// Re-export types for backwards-compatible imports from @/lib/api
export type { AutopsySummary, AutopsyReport, Certificate, EvidenceEntry, Build, GalleryApp, FileManifestEntry, TechStack, ComplexityTier, VersionEntry, RevivalPlan, RevivalFeature };

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function resolveDeployUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}

// ── Buildy API ──────────────────────────────────────────────────────────────

export async function getBuilds(): Promise<Build[]> {
  const res = await fetch(`${API_BASE}/api/builds`);
  if (!res.ok) return [];
  return res.json();
}

export async function getBuild(id: string): Promise<Build> {
  const res = await fetch(`${API_BASE}/api/builds/${id}`);
  if (!res.ok) throw new Error(`Build not found`);
  return res.json();
}

export async function createBuild(prompt: string): Promise<Build> {
  const res = await fetch(`${API_BASE}/api/builds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tweet_text: prompt }),
  });
  if (!res.ok) throw new Error(`Failed to create build: ${res.statusText}`);
  return res.json();
}

export async function modifyBuild(buildId: string, modification: string): Promise<Build> {
  const res = await fetch(`${API_BASE}/api/builds/${buildId}/modify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ modification }),
  });
  if (!res.ok) throw new Error(`Failed to modify build: ${res.statusText}`);
  return res.json();
}

export async function createBuildFromImage(imageBase64: string | string[], prompt?: string): Promise<Build> {
  const res = await fetch(`${API_BASE}/api/builds/from-image`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_base64: imageBase64, prompt: prompt || "" }),
  });
  if (!res.ok) throw new Error(`Failed to create build from image: ${res.statusText}`);
  return res.json();
}

export async function retryBuild(buildId: string): Promise<Build> {
  const res = await fetch(`${API_BASE}/api/builds/${buildId}/retry`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to retry build: ${res.statusText}`);
  return res.json();
}

export function getDownloadUrl(buildId: string): string {
  return `${API_BASE}/api/builds/${buildId}/download`;
}

export async function getBuildFiles(buildId: string): Promise<{ build_id: string; complexity: string; file_count: number; files: Record<string, string> }> {
  const res = await fetch(`${API_BASE}/api/builds/${buildId}/files`);
  if (!res.ok) throw new Error("Failed to fetch build files");
  return res.json();
}

export async function updateBuildFile(buildId: string, filePath: string, content: string): Promise<{ status: string; file_path: string; build_id: string }> {
  const res = await fetch(`${API_BASE}/api/builds/${buildId}/files`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path: filePath, content }),
  });
  if (!res.ok) throw new Error(`Failed to save file: ${res.statusText}`);
  return res.json();
}

export function streamBuild(buildId: string, onEvent: (event: { type: string; data: Record<string, unknown> }) => void): () => void {
  const url = `${API_BASE}/api/builds/${buildId}/stream`;
  const source = new EventSource(url);

  for (const evt of ["step", "file_generated", "file_streaming_start", "file_chunk", "status", "done"]) {
    source.addEventListener(evt, (e) => {
      const parsed = { type: evt, data: JSON.parse((e as MessageEvent).data) };
      if (evt === "done") source.close();
      onEvent(parsed);
    });
  }
  source.onerror = () => {
    // EventSource auto-reconnects, but close if too many failures
  };

  // Return cleanup function
  return () => source.close();
}

export async function getBuildChain(buildId: string): Promise<VersionEntry[]> {
  const res = await fetch(`${API_BASE}/api/builds/${buildId}/chain`);
  if (!res.ok) return [];
  return res.json();
}

export async function remixBuild(buildId: string, prompt: string): Promise<Build> {
  const res = await fetch(`${API_BASE}/api/builds/${buildId}/remix`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) throw new Error(`Failed to remix build: ${res.statusText}`);
  return res.json();
}

export interface CloudDeployResult {
  status: string;
  provider: string | null;
  url: string | null;
  instructions: CloudDeployInstructions | null;
}

export interface CloudDeployInstructions {
  message: string;
  repo_url?: string;
  download_first?: string;
  steps?: string[];
  docs_url?: string;
  options?: Array<{
    provider: string;
    name: string;
    steps: string[];
    one_liner: string | null;
    docs_url: string;
  }>;
}

export async function cloudDeploy(buildId: string, provider: string): Promise<Build> {
  const res = await fetch(`${API_BASE}/api/builds/${buildId}/cloud-deploy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Failed to deploy: ${res.statusText}`);
  }
  return res.json();
}

export async function getDeployStatus(buildId: string): Promise<CloudDeployResult> {
  const res = await fetch(`${API_BASE}/api/builds/${buildId}/deploy-status`);
  if (!res.ok) throw new Error("Failed to fetch deploy status");
  return res.json();
}

export async function getGallery(): Promise<GalleryApp[]> {
  const res = await fetch(`${API_BASE}/api/gallery`);
  if (!res.ok) return [];
  return res.json();
}

// ── Autopsy API ─────────────────────────────────────────────────────────────

const AUTOPSY_BASE = process.env.NEXT_PUBLIC_AUTOPSY_URL || "http://localhost:8001";

export async function createAutopsy(repoUrl: string): Promise<{ autopsy_id: string; status: string }> {
  const res = await fetch(`${AUTOPSY_BASE}/api/autopsy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
  if (!res.ok) throw new Error(`Failed to create autopsy: ${res.statusText}`);
  return res.json();
}

export async function getAutopsy(id: string): Promise<AutopsyReport> {
  const res = await fetch(`${AUTOPSY_BASE}/api/autopsy/${id}`);
  if (!res.ok) throw new Error(`Autopsy not found`);
  return res.json();
}

export async function getCertificate(id: string): Promise<Certificate> {
  const res = await fetch(`${AUTOPSY_BASE}/api/autopsy/${id}/certificate`);
  if (!res.ok) throw new Error(`Certificate not ready`);
  return res.json();
}

export async function getEvidence(id: string): Promise<EvidenceEntry[]> {
  const res = await fetch(`${AUTOPSY_BASE}/api/autopsy/${id}/evidence`);
  if (!res.ok) return [];
  return res.json();
}

export async function listAutopsies(): Promise<AutopsySummary[]> {
  const res = await fetch(`${AUTOPSY_BASE}/api/autopsies`);
  if (!res.ok) return [];
  return res.json();
}

export function createAutopsyStream(id: string): WebSocket {
  const wsBase = AUTOPSY_BASE.replace(/^http/, "ws");
  return new WebSocket(`${wsBase}/api/autopsy/${id}/stream`);
}

export async function startRevival(id: string): Promise<{ autopsy_id: string; revival_status: string }> {
  const res = await fetch(`${AUTOPSY_BASE}/api/autopsy/${id}/revive`, { method: "POST" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Failed to start revival: ${res.statusText}`);
  }
  return res.json();
}

export async function getRevival(id: string): Promise<{
  revival_status: string;
  revival_plan: RevivalPlan | null;
  revival_features: RevivalFeature[] | null;
  revival_created_at: string | null;
}> {
  const res = await fetch(`${AUTOPSY_BASE}/api/autopsy/${id}/revival`);
  if (!res.ok) throw new Error("Revival not found");
  return res.json();
}
