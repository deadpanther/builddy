"use client";

import { useState, useMemo, useCallback } from "react";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  File,
  FileCode,
  FileCode2,
  FileText,
  FileJson,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface FileExplorerProps {
  files: Record<string, string>;
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
  className?: string;
}

interface TreeNode {
  name: string;
  path: string;
  kind: "file" | "folder";
  children: TreeNode[];
}

/* ------------------------------------------------------------------ */
/*  Icon helpers                                                       */
/* ------------------------------------------------------------------ */

function fileIconFor(name: string) {
  const ext = name.includes(".") ? name.slice(name.lastIndexOf(".")) : "";

  switch (ext) {
    case ".js":
    case ".jsx":
    case ".ts":
    case ".tsx":
      return { Icon: FileCode, color: "text-yellow-400" };
    case ".html":
      return { Icon: FileCode2, color: "text-orange-400" };
    case ".css":
    case ".scss":
      return { Icon: FileText, color: "text-blue-400" };
    case ".json":
      return { Icon: FileJson, color: "text-green-400" };
    case ".md":
    case ".mdx":
      return { Icon: FileText, color: "text-purple-400" };
    case ".yml":
    case ".yaml":
      return { Icon: FileText, color: "text-neutral-500" };
    default:
      return { Icon: File, color: "text-neutral-500" };
  }
}

/* ------------------------------------------------------------------ */
/*  Tree builder                                                       */
/* ------------------------------------------------------------------ */

function buildTree(filePaths: readonly string[]): readonly TreeNode[] {
  const root: TreeNode[] = [];

  for (const filePath of filePaths) {
    const parts = filePath.split("/");
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isFile = i === parts.length - 1;
      const existing = current.find(
        (n) => n.name === part && n.kind === (isFile ? "file" : "folder"),
      );

      if (existing) {
        current = existing.children;
      } else {
        const node: TreeNode = {
          name: part,
          path: parts.slice(0, i + 1).join("/"),
          kind: isFile ? "file" : "folder",
          children: [],
        };
        current.push(node);
        current = node.children;
      }
    }
  }

  return sortTree(root);
}

function sortTree(nodes: readonly TreeNode[]): TreeNode[] {
  const folders = nodes
    .filter((n) => n.kind === "folder")
    .map((n) => ({ ...n, children: sortTree(n.children) }))
    .sort((a, b) => a.name.localeCompare(b.name));

  const files = [...nodes.filter((n) => n.kind === "file")].sort((a, b) =>
    a.name.localeCompare(b.name),
  );

  return [...folders, ...files];
}

/* ------------------------------------------------------------------ */
/*  Components                                                         */
/* ------------------------------------------------------------------ */

function TreeItem({
  node,
  depth,
  selectedFile,
  expandedPaths,
  onSelectFile,
  onToggleFolder,
}: {
  node: TreeNode;
  depth: number;
  selectedFile: string | null;
  expandedPaths: ReadonlySet<string>;
  onSelectFile: (path: string) => void;
  onToggleFolder: (path: string) => void;
}) {
  const isExpanded = expandedPaths.has(node.path);
  const isSelected = node.kind === "file" && node.path === selectedFile;
  const paddingLeft = `${depth * 12 + 8}px`;

  if (node.kind === "folder") {
    return (
      <>
        <button
          type="button"
          onClick={() => onToggleFolder(node.path)}
          className={cn(
            "flex w-full items-center gap-1.5 py-1 pr-2 font-mono text-xs text-neutral-500",
            "transition-colors hover:bg-neutral-800/50 hover:text-neutral-400",
          )}
          style={{ paddingLeft }}
        >
          {isExpanded ? (
            <ChevronDown className="h-3 w-3 shrink-0" />
          ) : (
            <ChevronRight className="h-3 w-3 shrink-0" />
          )}
          {isExpanded ? (
            <FolderOpen className="h-3.5 w-3.5 shrink-0 text-neutral-500" />
          ) : (
            <Folder className="h-3.5 w-3.5 shrink-0 text-neutral-500" />
          )}
          <span className="truncate">{node.name}</span>
        </button>

        {isExpanded &&
          node.children.map((child) => (
            <TreeItem
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedFile={selectedFile}
              expandedPaths={expandedPaths}
              onSelectFile={onSelectFile}
              onToggleFolder={onToggleFolder}
            />
          ))}
      </>
    );
  }

  const { Icon, color } = fileIconFor(node.name);

  return (
    <button
      type="button"
      onClick={() => onSelectFile(node.path)}
      className={cn(
        "flex w-full items-center gap-1.5 py-1 pr-2 font-mono text-xs",
        "transition-colors",
        isSelected
          ? "border-l-2 border-violet-500 bg-violet-900/30 text-violet-200"
          : "border-l-2 border-transparent text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-300",
      )}
      style={{ paddingLeft }}
    >
      <Icon className={cn("h-3.5 w-3.5 shrink-0", color)} />
      <span className="truncate">{node.name}</span>
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Main export                                                        */
/* ------------------------------------------------------------------ */

export function FileExplorer({
  files,
  selectedFile,
  onSelectFile,
  className,
}: FileExplorerProps) {
  const filePaths = useMemo(() => Object.keys(files), [files]);
  const tree = useMemo(() => buildTree(filePaths), [filePaths]);

  // Collect all folder paths so they start expanded
  const allFolderPaths = useMemo(() => {
    const paths = new Set<string>();
    function walk(nodes: readonly TreeNode[]) {
      for (const node of nodes) {
        if (node.kind === "folder") {
          paths.add(node.path);
          walk(node.children);
        }
      }
    }
    walk(tree);
    return paths;
  }, [tree]);

  const [expandedPaths, setExpandedPaths] = useState<ReadonlySet<string>>(
    () => allFolderPaths,
  );

  const handleToggleFolder = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const fileCount = filePaths.length;

  return (
    <div className={cn("flex flex-col", className)}>
      <div className="flex-1 overflow-y-auto py-1">
        {tree.map((node) => (
          <TreeItem
            key={node.path}
            node={node}
            depth={0}
            selectedFile={selectedFile}
            expandedPaths={expandedPaths}
            onSelectFile={onSelectFile}
            onToggleFolder={handleToggleFolder}
          />
        ))}
      </div>

      <div className="border-t border-neutral-800 px-3 py-2">
        <span className="font-mono text-[10px] text-neutral-600">
          {fileCount} {fileCount === 1 ? "file" : "files"}
        </span>
      </div>
    </div>
  );
}
