import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AgentSteps } from "@/components/AgentSteps";
import type { BuildStatus } from "@/lib/types";

describe("AgentSteps", () => {
  it("renders all pipeline steps", () => {
    render(<AgentSteps buildStatus="pending" />);
    expect(screen.getByText("Planning")).toBeInTheDocument();
    expect(screen.getByText("Coding")).toBeInTheDocument();
    expect(screen.getByText("Reviewing")).toBeInTheDocument();
    expect(screen.getByText("Deploying")).toBeInTheDocument();
  });

  it("shows step descriptions", () => {
    render(<AgentSteps buildStatus="pending" />);
    expect(screen.getByText(/Analyzing request and planning architecture/)).toBeInTheDocument();
    expect(screen.getByText(/Generating complete HTML\/CSS\/JS/)).toBeInTheDocument();
    expect(screen.getByText(/Self-reviewing code/)).toBeInTheDocument();
    expect(screen.getByText(/Deploying to static hosting/)).toBeInTheDocument();
  });

  it("shows pending state for all steps when build is pending", () => {
    render(<AgentSteps buildStatus="pending" />);
    // All steps should be in pending state (no "in progress" text)
    expect(screen.queryByText("in progress")).not.toBeInTheDocument();
  });

  it("shows active state for planning step", () => {
    render(<AgentSteps buildStatus="planning" />);
    expect(screen.getByText("in progress")).toBeInTheDocument();
  });

  it("shows active state for coding step", () => {
    render(<AgentSteps buildStatus="coding" />);
    expect(screen.getByText("in progress")).toBeInTheDocument();
  });

  it("shows active state for reviewing step", () => {
    render(<AgentSteps buildStatus="reviewing" />);
    expect(screen.getByText("in progress")).toBeInTheDocument();
  });

  it("shows active state for deploying step", () => {
    render(<AgentSteps buildStatus="deploying" />);
    expect(screen.getByText("in progress")).toBeInTheDocument();
  });

  it("shows all steps as done when deployed", () => {
    const { container } = render(<AgentSteps buildStatus="deployed" />);
    // Should have success class on all steps
    const successElements = container.querySelectorAll(".text-success");
    expect(successElements.length).toBeGreaterThan(0);
  });

  it("shows failed state when build failed", () => {
    render(<AgentSteps buildStatus="failed" />);
    expect(screen.getByText("Planning")).toBeInTheDocument();
  });

  it("shows failed state at specific step", () => {
    render(<AgentSteps buildStatus="failed" failedAtStatus="coding" />);
    expect(screen.getByText("Planning")).toBeInTheDocument();
    expect(screen.getByText("Coding")).toBeInTheDocument();
  });

  it("renders raw pipeline log when rawSteps provided", () => {
    const rawSteps = [
      "Starting build process",
      "Generating code",
      "Complete",
    ];
    
    render(<AgentSteps buildStatus="deployed" rawSteps={rawSteps} />);
    
    expect(screen.getByText("Pipeline Log")).toBeInTheDocument();
    expect(screen.getByText("Starting build process")).toBeInTheDocument();
    expect(screen.getByText("Generating code")).toBeInTheDocument();
    expect(screen.getByText("Complete")).toBeInTheDocument();
  });

  it("does not render pipeline log when rawSteps is empty", () => {
    render(<AgentSteps buildStatus="deployed" rawSteps={[]} />);
    expect(screen.queryByText("Pipeline Log")).not.toBeInTheDocument();
  });

  it("does not render pipeline log when rawSteps is undefined", () => {
    render(<AgentSteps buildStatus="deployed" />);
    expect(screen.queryByText("Pipeline Log")).not.toBeInTheDocument();
  });

  it("renders thinking badge for [thinking] steps", () => {
    const rawSteps = ["[thinking] Analyzing requirements"];
    render(<AgentSteps buildStatus="coding" rawSteps={rawSteps} />);
    
    expect(screen.getByText("Thinking")).toBeInTheDocument();
    expect(screen.getByText("Analyzing requirements")).toBeInTheDocument();
  });

  it("renders research badge for [research] steps", () => {
    const rawSteps = ["[research] Searching documentation"];
    render(<AgentSteps buildStatus="coding" rawSteps={rawSteps} />);
    
    expect(screen.getByText("Web Search")).toBeInTheDocument();
    expect(screen.getByText("Searching documentation")).toBeInTheDocument();
  });

  it("renders image badge for [image] steps", () => {
    const rawSteps = ["[image] Generating thumbnail"];
    render(<AgentSteps buildStatus="coding" rawSteps={rawSteps} />);
    
    expect(screen.getByText("CogView-4")).toBeInTheDocument();
    expect(screen.getByText("Generating thumbnail")).toBeInTheDocument();
  });

  it("renders manifest badge for [manifest] steps", () => {
    const rawSteps = ["[manifest] Building file list"];
    render(<AgentSteps buildStatus="coding" rawSteps={rawSteps} />);
    
    expect(screen.getByText("Manifest")).toBeInTheDocument();
    expect(screen.getByText("Building file list")).toBeInTheDocument();
  });

  it("renders integration badge for [integration] steps", () => {
    const rawSteps = ["[integration] Connecting services"];
    render(<AgentSteps buildStatus="coding" rawSteps={rawSteps} />);
    
    expect(screen.getByText("Integration")).toBeInTheDocument();
    expect(screen.getByText("Connecting services")).toBeInTheDocument();
  });

  it("numbers raw steps sequentially", () => {
    const rawSteps = ["Step 1", "Step 2", "Step 3"];
    render(<AgentSteps buildStatus="deployed" rawSteps={rawSteps} />);
    
    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
    expect(screen.getByText("03")).toBeInTheDocument();
  });

  it("highlights failed steps in red", () => {
    const rawSteps = ["Build started", "Build failed with error"];
    const { container } = render(<AgentSteps buildStatus="failed" rawSteps={rawSteps} />);
    
    // Check that the step text is rendered and contains "failed"
    expect(screen.getByText(/Build failed with error/)).toBeInTheDocument();
    
    // Check that it has the danger color class
    const failedStep = screen.getByText(/Build failed with error/);
    expect(failedStep).toHaveClass("text-danger");
  });

  it("renders step icons for different states", () => {
    const { container } = render(<AgentSteps buildStatus="coding" />);
    
    // Should have spinner for active step
    const spinner = container.querySelector(".animate-spin");
    expect(spinner).toBeInTheDocument();
  });
});
