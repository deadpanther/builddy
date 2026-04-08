import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { FileExplorer } from "@/components/FileExplorer";

describe("FileExplorer", () => {
  const mockFiles: Record<string, string> = {
    "index.html": "<html></html>",
    "styles.css": "body {}",
    "app.js": "console.log('test');",
  };

  const mockOnSelectFile = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all files", () => {
    render(
      <FileExplorer
        files={mockFiles}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    expect(screen.getByText("index.html")).toBeInTheDocument();
    expect(screen.getByText("styles.css")).toBeInTheDocument();
    expect(screen.getByText("app.js")).toBeInTheDocument();
  });

  it("displays file count", () => {
    render(
      <FileExplorer
        files={mockFiles}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    expect(screen.getByText("3 files")).toBeInTheDocument();
  });

  it("displays singular file count for one file", () => {
    const singleFile = { "index.html": "<html></html>" };
    render(
      <FileExplorer
        files={singleFile}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    expect(screen.getByText("1 file")).toBeInTheDocument();
  });

  it("calls onSelectFile when file is clicked", () => {
    render(
      <FileExplorer
        files={mockFiles}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    
    const indexFile = screen.getByText("index.html");
    fireEvent.click(indexFile);
    
    expect(mockOnSelectFile).toHaveBeenCalledWith("index.html");
  });

  it("highlights selected file", () => {
    const { container } = render(
      <FileExplorer
        files={mockFiles}
        selectedFile="index.html"
        onSelectFile={mockOnSelectFile}
      />
    );
    
    const selectedButton = container.querySelector(".border-violet-500");
    expect(selectedButton).toHaveTextContent("index.html");
  });

  it("renders nested folder structure", () => {
    const nestedFiles: Record<string, string> = {
      "src/index.js": "code",
      "src/components/App.js": "component",
      "src/styles/main.css": "styles",
      "package.json": "{}",
    };
    
    render(
      <FileExplorer
        files={nestedFiles}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    
    expect(screen.getByText("src")).toBeInTheDocument();
    expect(screen.getByText("components")).toBeInTheDocument();
    expect(screen.getByText("styles")).toBeInTheDocument();
    expect(screen.getByText("package.json")).toBeInTheDocument();
  });

  it("folders are expanded by default", () => {
    const nestedFiles: Record<string, string> = {
      "src/index.js": "code",
      "src/components/App.js": "component",
    };
    
    render(
      <FileExplorer
        files={nestedFiles}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    
    // Should show nested files immediately
    expect(screen.getByText("index.js")).toBeInTheDocument();
    expect(screen.getByText("App.js")).toBeInTheDocument();
  });

  it("can collapse and expand folders", () => {
    const nestedFiles: Record<string, string> = {
      "src/index.js": "code",
    };
    
    render(
      <FileExplorer
        files={nestedFiles}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    
    // File should be visible initially
    expect(screen.getByText("index.js")).toBeInTheDocument();
    
    // Click folder to collapse
    const srcFolder = screen.getByText("src");
    fireEvent.click(srcFolder);
    
    // File should now be hidden
    expect(screen.queryByText("index.js")).not.toBeInTheDocument();
    
    // Click folder to expand again
    fireEvent.click(srcFolder);
    
    // File should be visible again
    expect(screen.getByText("index.js")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <FileExplorer
        files={mockFiles}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
        className="custom-class"
      />
    );
    
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain("custom-class");
  });

  it("renders appropriate icons for different file types", () => {
    const files: Record<string, string> = {
      "app.js": "js",
      "component.tsx": "tsx",
      "index.html": "html",
      "styles.css": "css",
      "data.json": "json",
      "readme.md": "md",
    };
    
    const { container } = render(
      <FileExplorer
        files={files}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    
    // Just check that the component renders without errors
    expect(screen.getByText("app.js")).toBeInTheDocument();
    expect(screen.getByText("component.tsx")).toBeInTheDocument();
    expect(screen.getByText("index.html")).toBeInTheDocument();
  });

  it("handles empty files object", () => {
    render(
      <FileExplorer
        files={{}}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    
    expect(screen.getByText("0 files")).toBeInTheDocument();
  });

  it("sorts folders before files", () => {
    const mixedFiles: Record<string, string> = {
      "zebra.js": "code",
      "alpha/beta.js": "nested",
      "alpha.js": "code2",
    };
    
    render(
      <FileExplorer
        files={mixedFiles}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    
    const buttons = screen.getAllByRole("button");
    const buttonTexts = buttons.map(b => b.textContent);
    
    // "alpha" folder should come before "alpha.js" and "zebra.js"
    const alphaIndex = buttonTexts.findIndex(t => t?.includes("alpha") && !t?.includes(".js"));
    const alphaJsIndex = buttonTexts.findIndex(t => t?.includes("alpha.js"));
    
    expect(alphaIndex).toBeLessThan(alphaJsIndex);
  });

  it("sorts files alphabetically", () => {
    const files: Record<string, string> = {
      "c.js": "c",
      "a.js": "a",
      "b.js": "b",
    };
    
    render(
      <FileExplorer
        files={files}
        selectedFile={null}
        onSelectFile={mockOnSelectFile}
      />
    );
    
    const buttons = screen.getAllByRole("button");
    const buttonTexts = buttons.map(b => b.textContent);
    
    // Find indices for each file
    const aIndex = buttonTexts.findIndex(t => t?.includes("a.js"));
    const bIndex = buttonTexts.findIndex(t => t?.includes("b.js"));
    const cIndex = buttonTexts.findIndex(t => t?.includes("c.js"));
    
    // a should come before b, b before c
    expect(aIndex).toBeLessThan(bIndex);
    expect(bIndex).toBeLessThan(cIndex);
  });
});
