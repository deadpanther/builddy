export type BuildStatus =
  | "pending"
  | "planning"
  | "coding"
  | "reviewing"
  | "deploying"
  | "deployed"
  | "failed";

export interface AgentStep {
  step: string;
  title: string;
  description?: string;
  status: "pending" | "active" | "done" | "failed";
  output?: string;
  timestamp?: string;
}

export interface Build {
  id: string;
  tweet_id?: string;
  tweet_text?: string;
  twitter_username?: string;
  app_name?: string;
  app_description?: string;
  prompt?: string;
  status: BuildStatus;
  generated_code?: string;
  deploy_url?: string;
  parent_build_id?: string;
  steps?: string; // JSON-encoded AgentStep[]
  error?: string;
  created_at: string;
  updated_at?: string;
  deployed_at?: string;
}

export interface GalleryApp {
  id: string;
  app_name: string;
  app_description: string;
  deploy_url: string;
  tweet_text: string;
  twitter_username?: string;
  deployed_at: string;
}

// Autopsy types (existing)
export interface AutopsySummary {
  id: string;
  repo_name: string;
  repo_url: string;
  status: string;
  cause_of_death: string | null;
  created_at: string | null;
}

export interface TimelineEvent {
  date: string;
  event: string;
  severity: "critical" | "warning" | "info";
  evidence: string;
}

export interface FatalCommit {
  hash: string;
  date: string;
  message: string;
  why_fatal: string;
}

export interface AutopsyReport {
  id: string;
  repo_url: string;
  repo_name: string;
  status: string;
  cause_of_death: string | null;
  contributing_factors: string[] | null;
  timeline: TimelineEvent[] | null;
  fatal_commits: FatalCommit[] | null;
  findings: Record<string, unknown> | null;
  lessons_learned: string[] | null;
  error_message: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface Certificate {
  certificate_number: string;
  repository: string;
  repository_url: string;
  date_of_birth: string;
  date_of_death: string;
  cause_of_death: string;
  contributing_factors: string[];
  examining_pathologist: string;
  date_of_examination: string;
  findings_summary: Record<string, unknown>;
  lessons: string[];
}

export interface EvidenceEntry {
  id: string;
  phase: string;
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  observation: string | null;
  created_at: string | null;
}
