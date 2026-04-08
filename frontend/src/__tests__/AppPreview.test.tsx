import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AppPreview } from "@/components/AppPreview";

// Mock window.open
const mockOpen = vi.fn();
window.open = mockOpen;

describe("AppPreview", () => {
  const testUrl = "https://example.com/app";

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the preview component with URL", () => {
    render(<AppPreview url={testUrl} />);
    expect(screen.getByText(testUrl)).toBeInTheDocument();
  });

  it("renders browser chrome with traffic lights", () => {
    const { container } = render(<AppPreview url={testUrl} />);
    const redLight = container.querySelector(".bg-red-500\\/70");
    const yellowLight = container.querySelector(".bg-yellow-500\\/70");
    const greenLight = container.querySelector(".bg-green-500\\/70");
    expect(redLight).toBeInTheDocument();
    expect(yellowLight).toBeInTheDocument();
    expect(greenLight).toBeInTheDocument();
  });

  it("renders iframe with correct src", () => {
    const { container } = render(<AppPreview url={testUrl} />);
    const iframe = container.querySelector("iframe");
    expect(iframe).toHaveAttribute("src", testUrl);
    expect(iframe).toHaveAttribute("title", "App Preview");
  });

  it("renders iframe with correct sandbox attributes", () => {
    const { container } = render(<AppPreview url={testUrl} />);
    const iframe = container.querySelector("iframe");
    expect(iframe).toHaveAttribute("sandbox", "allow-scripts allow-same-origin allow-forms allow-popups");
  });

  it("reloads iframe when refresh button is clicked", () => {
    const { container, getByTitle } = render(<AppPreview url={testUrl} />);
    const iframe = container.querySelector("iframe");
    
    const refreshButton = getByTitle("Reload");
    fireEvent.click(refreshButton);
    
    // The iframe should still exist after reload
    const newIframe = container.querySelector("iframe");
    expect(newIframe).toBeInTheDocument();
  });

  it("opens URL in new tab when maximize button is clicked", () => {
    const { getByTitle } = render(<AppPreview url={testUrl} />);
    const maximizeButton = getByTitle("Open in new tab");
    
    // The button is actually an anchor tag with target="_blank"
    expect(maximizeButton).toHaveAttribute("href", testUrl);
    expect(maximizeButton).toHaveAttribute("target", "_blank");
    expect(maximizeButton).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows backend live indicator when hasBackend is true", () => {
    render(<AppPreview url={testUrl} hasBackend />);
    expect(screen.getByText("Backend live")).toBeInTheDocument();
  });

  it("hides backend live indicator when hasBackend is false", () => {
    render(<AppPreview url={testUrl} hasBackend={false} />);
    expect(screen.queryByText("Backend live")).not.toBeInTheDocument();
  });

  it("hides backend live indicator by default", () => {
    render(<AppPreview url={testUrl} />);
    expect(screen.queryByText("Backend live")).not.toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<AppPreview url={testUrl} className="custom-class" />);
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain("custom-class");
  });

  it("renders with empty URL", () => {
    const { container } = render(<AppPreview url="" />);
    const iframe = container.querySelector("iframe");
    expect(iframe).toHaveAttribute("src", "");
  });

  it("truncates long URLs", () => {
    const longUrl = "https://example.com/very/long/path/that/should/be/truncated/because/it/is/too/long";
    render(<AppPreview url={longUrl} />);
    const urlElement = screen.getByText(longUrl);
    expect(urlElement).toHaveClass("truncate");
  });
});
