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

export type ComplexityTier = "simple" | "standard" | "fullstack";

export interface Build {
  id: string;
  tweet_id?: string;
  tweet_text?: string;
  tweet_url?: string;
  twitter_username?: string;
  app_name?: string;
  app_description?: string;
  prompt?: string;
  status: BuildStatus;
  generated_code?: string;
  deploy_url?: string;
  parent_build_id?: string;
  build_type?: "text" | "screenshot";
  complexity?: ComplexityTier;
  thumbnail_url?: string;
  reasoning_log?: string; // JSON-encoded reasoning entries
  file_manifest?: string; // JSON-encoded FileManifestEntry[]
  generated_files?: string; // JSON-encoded {filepath: content}
  zip_url?: string;
  tech_stack?: string; // JSON-encoded TechStack
  deploy_provider?: string;
  deploy_external_url?: string;
  deploy_status?: string;
  steps?: string; // JSON-encoded AgentStep[]
  error?: string;
  created_at: string;
  updated_at?: string;
  deployed_at?: string;
}

export interface FileManifestEntry {
  path: string;
  purpose: string;
  order: number;
  generates_api?: string[];
  uses_api?: string[];
  tables?: string[];
  pages?: string[];
  dependencies?: string[];
}

export interface TechStack {
  frontend: string;
  backend: string;
  database: string;
  deployment: string;
}

export interface ReasoningEntry {
  stage: string;
  reasoning: string;
}

export interface VersionEntry {
  id: string;
  app_name?: string;
  prompt?: string;
  status: string;
  complexity?: string;
  created_at: string;
  parent_build_id?: string;
}

export interface GalleryApp {
  id: string;
  app_name: string;
  app_description: string;
  deploy_url: string;
  tweet_text: string;
  twitter_username?: string;
  build_type?: string;
  complexity?: string;
  tech_stack?: string;
  zip_url?: string;
  remix_count?: number;
  thumbnail_url?: string;
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
  health_score: number | null;
  prognosis: string | null;
  lessons_learned: string[] | null;
  error_message: string | null;
  created_at: string | null;
  completed_at: string | null;
  revival_status: string | null;
}

export interface RevivalAction {
  action: string;
  target: string;
  rationale: string;
  difficulty: "easy" | "moderate" | "hard";
}

export interface RevivalPhase {
  phase_number: number;
  title: string;
  description: string;
  estimated_effort: string;
  actions: RevivalAction[];
}

export interface RevivalPlan {
  executive_summary: string;
  priority: "critical" | "high" | "medium" | "low";
  phases: RevivalPhase[];
  quick_wins: string[];
  tech_debt_payoff_order?: string[];
  architecture_recommendations?: string;
  testing_strategy?: string;
  dependency_overhaul?: string;
  security_fixes?: string[];
  community_revival_plan?: string;
}

export interface RevivalFeature {
  title: string;
  description: string;
  why_this_changes_everything: string;
  technical_approach: string;
  impact: "transformative" | "high" | "moderate";
  effort: "small" | "medium" | "large";
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
