// Pipeline Designer Types

export type NodeType =
  | "input"      // Text/Screenshot input
  | "planner"    // Planning stage
  | "coder"      // Code generation
  | "reviewer"   // Code review
  | "autopilot"  // Auto-fix loop
  | "test_gen"   // Test generation
  | "deployer"   // Deployment
  | "condition"  // Conditional branching
  | "parallel"   // Parallel execution
  | "llm"        // Custom LLM call
  | "webhook"    // External webhook
  | "transform"  // Data transformation
  | "output";    // Final output

export interface PipelineNode {
  id: string;
  type: NodeType;
  label: string;
  config: Record<string, unknown>;
  position: { x: number; y: number };
  inputs: string[];  // IDs of connected output ports
  outputs: string[]; // IDs of connected input ports
}

export interface PipelineEdge {
  id: string;
  source: string;  // Node ID
  sourcePort: string;
  target: string;  // Node ID
  targetPort: string;
  condition?: string; // For conditional edges
}

export interface PipelineConfig {
  id: string;
  name: string;
  description?: string;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  variables: Record<string, string>;
  created_at: string;
  updated_at: string;
}

// Node type configurations
export const NODE_TYPES: Record<NodeType, {
  label: string;
  description: string;
  icon: string;
  color: string;
  inputs: string[];
  outputs: string[];
  configFields: ConfigField[];
}> = {
  input: {
    label: "Input",
    description: "Text or screenshot input",
    icon: "FileText",
    color: "sky",
    inputs: [],
    outputs: ["prompt", "context"],
    configFields: [
      { name: "input_type", type: "select", options: ["text", "screenshot"], default: "text" },
      { name: "max_length", type: "number", default: 500 },
    ],
  },
  planner: {
    label: "Planner",
    description: "Analyze and plan architecture",
    icon: "Brain",
    color: "violet",
    inputs: ["prompt"],
    outputs: ["plan", "tech_stack"],
    configFields: [
      { name: "model", type: "select", options: ["glm-5.1", "claude-sonnet", "gpt-4"], default: "glm-5.1" },
      { name: "thinking_mode", type: "boolean", default: true },
    ],
  },
  coder: {
    label: "Coder",
    description: "Generate code",
    icon: "Code",
    color: "emerald",
    inputs: ["plan", "tech_stack"],
    outputs: ["code", "files"],
    configFields: [
      { name: "model", type: "select", options: ["glm-5.1", "claude-sonnet"], default: "glm-5.1" },
      { name: "multi_file", type: "boolean", default: false },
      { name: "framework", type: "select", options: ["vanilla", "react", "vue", "nextjs"], default: "vanilla" },
    ],
  },
  reviewer: {
    label: "Reviewer",
    description: "Review and validate code",
    icon: "Search",
    color: "amber",
    inputs: ["code", "files"],
    outputs: ["approved", "issues"],
    configFields: [
      { name: "auto_fix", type: "boolean", default: true },
      { name: "max_iterations", type: "number", default: 3 },
    ],
  },
  autopilot: {
    label: "Autopilot",
    description: "Auto-fix loop for browser errors",
    icon: "RefreshCw",
    color: "orange",
    inputs: ["code", "files"],
    outputs: ["fixed_code", "fixed_files"],
    configFields: [
      { name: "max_iterations", type: "number", default: 5 },
      { name: "browser_type", type: "select", options: ["chromium", "firefox", "webkit"], default: "chromium" },
    ],
  },
  test_gen: {
    label: "Test Generator",
    description: "Generate tests for code",
    icon: "FlaskConical",
    color: "teal",
    inputs: ["code", "files"],
    outputs: ["tests"],
    configFields: [
      { name: "framework", type: "select", options: ["pytest", "jest", "vitest"], default: "pytest" },
      { name: "coverage_target", type: "number", default: 80 },
    ],
  },
  deployer: {
    label: "Deployer",
    description: "Deploy to hosting",
    icon: "Rocket",
    color: "rose",
    inputs: ["code", "files"],
    outputs: ["url", "status"],
    configFields: [
      { name: "provider", type: "select", options: ["local", "railway", "render", "vercel"], default: "local" },
      { name: "auto_rollback", type: "boolean", default: true },
    ],
  },
  condition: {
    label: "Condition",
    description: "Branch based on condition",
    icon: "GitBranch",
    color: "yellow",
    inputs: ["input"],
    outputs: ["true", "false"],
    configFields: [
      { name: "expression", type: "text", default: "input.status === 'success'" },
    ],
  },
  parallel: {
    label: "Parallel",
    description: "Execute branches in parallel",
    icon: "Layers",
    color: "cyan",
    inputs: ["input"],
    outputs: ["branch_1", "branch_2", "branch_3"],
    configFields: [
      { name: "branches", type: "number", default: 2 },
    ],
  },
  llm: {
    label: "LLM Call",
    description: "Custom LLM prompt",
    icon: "MessageSquare",
    color: "indigo",
    inputs: ["input"],
    outputs: ["output"],
    configFields: [
      { name: "model", type: "select", options: ["glm-5.1", "claude-sonnet", "gpt-4"], default: "glm-5.1" },
      { name: "prompt_template", type: "textarea", default: "" },
      { name: "temperature", type: "number", default: 0.7 },
    ],
  },
  webhook: {
    label: "Webhook",
    description: "Call external API",
    icon: "Link",
    color: "slate",
    inputs: ["input"],
    outputs: ["output"],
    configFields: [
      { name: "url", type: "text", default: "" },
      { name: "method", type: "select", options: ["GET", "POST", "PUT", "DELETE"], default: "POST" },
      { name: "headers", type: "json", default: "{}" },
    ],
  },
  transform: {
    label: "Transform",
    description: "Transform data",
    icon: "Wrench",
    color: "stone",
    inputs: ["input"],
    outputs: ["output"],
    configFields: [
      { name: "transform_type", type: "select", options: ["jsonpath", "jmespath", "custom"], default: "jsonpath" },
      { name: "expression", type: "text", default: "" },
    ],
  },
  output: {
    label: "Output",
    description: "Final output",
    icon: "CheckCircle",
    color: "green",
    inputs: ["result"],
    outputs: [],
    configFields: [
      { name: "save_to_db", type: "boolean", default: true },
      { name: "notify", type: "boolean", default: false },
    ],
  },
};

export interface ConfigField {
  name: string;
  type: "text" | "textarea" | "number" | "boolean" | "select" | "json";
  options?: string[];
  default: unknown;
}

// Default pipeline templates
export const DEFAULT_PIPELINES: PipelineConfig[] = [
  {
    id: "standard",
    name: "Standard Build",
    description: "Standard text-to-app pipeline",
    nodes: [
      { id: "input-1", type: "input", label: "Input", config: { input_type: "text" }, position: { x: 50, y: 100 }, inputs: [], outputs: ["planner-1"] },
      { id: "planner-1", type: "planner", label: "Plan", config: {}, position: { x: 250, y: 100 }, inputs: ["input-1"], outputs: ["coder-1"] },
      { id: "coder-1", type: "coder", label: "Code", config: {}, position: { x: 450, y: 100 }, inputs: ["planner-1"], outputs: ["reviewer-1"] },
      { id: "reviewer-1", type: "reviewer", label: "Review", config: {}, position: { x: 650, y: 100 }, inputs: ["coder-1"], outputs: ["deployer-1"] },
      { id: "deployer-1", type: "deployer", label: "Deploy", config: {}, position: { x: 850, y: 100 }, inputs: ["reviewer-1"], outputs: ["output-1"] },
      { id: "output-1", type: "output", label: "Done", config: {}, position: { x: 1050, y: 100 }, inputs: ["deployer-1"], outputs: [] },
    ],
    edges: [],
    variables: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "enhanced",
    name: "Enhanced Build",
    description: "With autopilot and test generation",
    nodes: [
      { id: "input-1", type: "input", label: "Input", config: { input_type: "text" }, position: { x: 50, y: 150 }, inputs: [], outputs: ["planner-1"] },
      { id: "planner-1", type: "planner", label: "Plan", config: {}, position: { x: 250, y: 150 }, inputs: ["input-1"], outputs: ["coder-1"] },
      { id: "coder-1", type: "coder", label: "Code", config: { multi_file: true }, position: { x: 450, y: 150 }, inputs: ["planner-1"], outputs: ["autopilot-1"] },
      { id: "autopilot-1", type: "autopilot", label: "Autopilot", config: {}, position: { x: 650, y: 150 }, inputs: ["coder-1"], outputs: ["reviewer-1"] },
      { id: "reviewer-1", type: "reviewer", label: "Review", config: {}, position: { x: 850, y: 100 }, inputs: ["autopilot-1"], outputs: ["deployer-1"] },
      { id: "test_gen-1", type: "test_gen", label: "Tests", config: {}, position: { x: 850, y: 200 }, inputs: ["autopilot-1"], outputs: ["deployer-1"] },
      { id: "deployer-1", type: "deployer", label: "Deploy", config: {}, position: { x: 1050, y: 150 }, inputs: ["reviewer-1", "test_gen-1"], outputs: ["output-1"] },
      { id: "output-1", type: "output", label: "Done", config: {}, position: { x: 1250, y: 150 }, inputs: ["deployer-1"], outputs: [] },
    ],
    edges: [],
    variables: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];
