import { describe, it, expect, vi, beforeEach } from "vitest";
import { resolveDeployUrl, API_BASE } from "@/lib/api";

describe("resolveDeployUrl", () => {
  it("returns null for null input", () => {
    expect(resolveDeployUrl(null)).toBeNull();
  });

  it("returns null for undefined input", () => {
    expect(resolveDeployUrl(undefined)).toBeNull();
  });

  it("returns null for empty string", () => {
    expect(resolveDeployUrl("")).toBeNull();
  });

  it("returns absolute URLs unchanged", () => {
    const url = "https://example.com/app";
    expect(resolveDeployUrl(url)).toBe(url);
  });

  it("returns http URLs unchanged", () => {
    const url = "http://localhost:8000/apps/123";
    expect(resolveDeployUrl(url)).toBe(url);
  });

  it("prepends API_BASE to relative paths", () => {
    const path = "/apps/abc-123/index.html";
    expect(resolveDeployUrl(path)).toBe(`${API_BASE}${path}`);
  });
});

describe("API_BASE", () => {
  it("has a default value", () => {
    expect(API_BASE).toBeTruthy();
    expect(typeof API_BASE).toBe("string");
  });

  it("starts with http", () => {
    expect(API_BASE.startsWith("http")).toBe(true);
  });
});
