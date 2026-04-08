import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "@/components/StatusBadge";
import type { BuildStatus } from "@/lib/types";

describe("StatusBadge", () => {
  const statuses: BuildStatus[] = [
    "pending",
    "planning",
    "coding",
    "reviewing",
    "deploying",
    "deployed",
    "failed",
  ];

  it.each(statuses)("renders %s status with correct label", (status) => {
    render(<StatusBadge status={status} />);
    const expected = status.charAt(0).toUpperCase() + status.slice(1);
    expect(screen.getByText(expected)).toBeInTheDocument();
  });

  it("renders deployed with green styling", () => {
    const { container } = render(<StatusBadge status="deployed" />);
    const badge = container.firstElementChild;
    expect(badge?.className).toContain("success");
  });

  it("renders failed with danger styling", () => {
    const { container } = render(<StatusBadge status="failed" />);
    const badge = container.firstElementChild;
    expect(badge?.className).toContain("danger");
  });

  it("renders coding with pulse animation", () => {
    const { container } = render(<StatusBadge status="coding" />);
    const dot = container.querySelector("span span");
    expect(dot?.className).toContain("animate-pulse");
  });

  it("accepts additional className", () => {
    const { container } = render(
      <StatusBadge status="pending" className="extra-class" />
    );
    const badge = container.firstElementChild;
    expect(badge?.className).toContain("extra-class");
  });

  it("falls back to pending config for unknown status", () => {
    render(<StatusBadge status={"unknown" as BuildStatus} />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });
});
