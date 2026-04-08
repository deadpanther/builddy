import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CodePreview } from "@/components/CodePreview";

// Mock clipboard API
const mockWriteText = vi.fn();
Object.assign(navigator, {
  clipboard: {
    writeText: mockWriteText,
  },
});

describe("CodePreview", () => {
  const testCode = '<div>Hello World</div>';
  
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the code content", () => {
    render(<CodePreview code={testCode} />);
    expect(screen.getByText(testCode)).toBeInTheDocument();
  });

  it("renders with default language (html)", () => {
    render(<CodePreview code={testCode} />);
    expect(screen.getByText("html")).toBeInTheDocument();
  });

  it("renders with custom language", () => {
    render(<CodePreview code={testCode} language="javascript" />);
    expect(screen.getByText("javascript")).toBeInTheDocument();
  });

  it("renders browser chrome with traffic lights", () => {
    const { container } = render(<CodePreview code={testCode} />);
    const redLight = container.querySelector(".bg-red-500\\/70");
    const yellowLight = container.querySelector(".bg-yellow-500\\/70");
    const greenLight = container.querySelector(".bg-green-500\\/70");
    expect(redLight).toBeInTheDocument();
    expect(yellowLight).toBeInTheDocument();
    expect(greenLight).toBeInTheDocument();
  });

  it("renders copy button", () => {
    render(<CodePreview code={testCode} />);
    expect(screen.getByText("Copy")).toBeInTheDocument();
  });

  it("copies code to clipboard when copy button is clicked", async () => {
    mockWriteText.mockResolvedValueOnce(undefined);
    
    render(<CodePreview code={testCode} />);
    const copyButton = screen.getByText("Copy").closest("button");
    fireEvent.click(copyButton!);
    
    expect(mockWriteText).toHaveBeenCalledWith(testCode);
  });

  it("shows 'Copied' state after copying", async () => {
    mockWriteText.mockResolvedValueOnce(undefined);
    
    render(<CodePreview code={testCode} />);
    const copyButton = screen.getByText("Copy").closest("button");
    fireEvent.click(copyButton!);
    
    await waitFor(() => {
      expect(screen.getByText("Copied")).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it("applies custom className", () => {
    const { container } = render(<CodePreview code={testCode} className="custom-class" />);
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain("custom-class");
  });

  it("renders pre element with code", () => {
    const { container } = render(<CodePreview code={testCode} />);
    const preElement = container.querySelector("pre");
    expect(preElement).toBeInTheDocument();
    expect(preElement).toHaveClass("font-mono");
  });

  it("renders code element inside pre", () => {
    const { container } = render(<CodePreview code={testCode} />);
    const codeElement = container.querySelector("pre code");
    expect(codeElement).toBeInTheDocument();
    expect(codeElement).toHaveTextContent(testCode);
  });

  it("handles empty code", () => {
    const { container } = render(<CodePreview code="" />);
    const codeElement = container.querySelector("pre code");
    expect(codeElement).toBeInTheDocument();
  });

  it("handles multi-line code", () => {
    const multiLineCode = `line1
line2
line3`;
    const { container } = render(<CodePreview code={multiLineCode} />);
    const codeElement = container.querySelector("pre code");
    expect(codeElement).toHaveTextContent("line1");
    expect(codeElement).toHaveTextContent("line2");
    expect(codeElement).toHaveTextContent("line3");
  });

  it("shows check state when copied", async () => {
    mockWriteText.mockResolvedValueOnce(undefined);
    
    const { container } = render(<CodePreview code={testCode} />);
    const copyButton = screen.getByText("Copy").closest("button");
    
    await act(async () => {
      fireEvent.click(copyButton!);
    });
    
    await waitFor(() => {
      expect(screen.getByText("Copied")).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});
