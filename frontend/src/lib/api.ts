import type { Build, GalleryApp, AutopsySummary, AutopsyReport, Certificate, EvidenceEntry } from "./types";

// Re-export types for backwards-compatible imports from @/lib/api
export type { AutopsySummary, AutopsyReport, Certificate, EvidenceEntry, Build, GalleryApp };

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
