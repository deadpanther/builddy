"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getBuild, streamBuild, getBuildFiles, getBuildChain } from "@/lib/api";
import type { Build, VersionEntry } from "@/lib/types";

const ACTIVE_STATUSES = new Set(["pending", "planning", "coding", "reviewing", "deploying"]);

interface UseBuildResult {
  build: Build | null;
  loadError: boolean;
  projectFiles: Record<string, string> | null;
  selectedFile: string | null;
  setSelectedFile: (file: string | null) => void;
  filesLoading: boolean;
  versionChain: VersionEntry[];
  liveStep: string | null;
  currentFile: string | null;
  streamingFile: string | null;
  streamingContent: string;
  previewKey: number;
  refreshPreview: () => void;
}

export function useBuild(id: string | undefined): UseBuildResult {
  const [build, setBuild] = useState<Build | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [projectFiles, setProjectFiles] = useState<Record<string, string> | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [filesLoading, setFilesLoading] = useState(false);
  const [versionChain, setVersionChain] = useState<VersionEntry[]>([]);
  const [liveStep, setLiveStep] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<string | null>(null);
  const [streamingFile, setStreamingFile] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState<string>("");
  const [previewKey, setPreviewKey] = useState(0);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const filesIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sseCleanupRef = useRef<(() => void) | null>(null);

  // Fetch build on mount and poll while active
  useEffect(() => {
    if (!id) return;
    let failCount = 0;

    const fetchBuild = () => {
      getBuild(id)
        .then((data) => {
          setBuild(data);
          setLoadError(false);
          failCount = 0;
        })
        .catch(() => {
          failCount++;
          if (failCount >= 3) setLoadError(true);
        });
    };

    fetchBuild();
    intervalRef.current = setInterval(fetchBuild, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [id]);

  // Stop polling when build reaches terminal state
  useEffect(() => {
    if (build && !ACTIVE_STATUSES.has(build.status) && intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [build]);

  // SSE streaming
  useEffect(() => {
    if (!id || !build) return;
    if (!ACTIVE_STATUSES.has(build.status)) {
      setLiveStep(null);
      setCurrentFile(null);
      return;
    }

    if (sseCleanupRef.current) sseCleanupRef.current();

    const cleanup = streamBuild(id, (event) => {
      if (event.type === "step") {
        const step = event.data.step as string;
        setLiveStep(step);
        const fileMatch = step.match(/Generating file \d+\/\d+: (.+)/);
        if (fileMatch) setCurrentFile(fileMatch[1]);
        const doneMatch = step.match(/Generated (.+?) \(/);
        if (doneMatch) setCurrentFile(null);
      }
      if (event.type === "file_streaming_start") {
        const path = event.data.file_path as string;
        setStreamingFile(path);
        setStreamingContent("");
        setSelectedFile(path);
      }
      if (event.type === "file_chunk") {
        const content = event.data.content as string;
        const path = event.data.file_path as string;
        const done = event.data.done as boolean;
        setStreamingContent(content);
        setStreamingFile(path);
        setSelectedFile(path);
        if (done) {
          setStreamingFile(null);
          setStreamingContent("");
        }
      }
      if (event.type === "file_generated") {
        getBuildFiles(id).then((data) => {
          setProjectFiles(data.files);
          const path = event.data.file_path as string;
          setSelectedFile(path);
        }).catch(() => {});
        setCurrentFile(null);
        setStreamingFile(null);
        setStreamingContent("");
      }
      if (event.type === "status") {
        getBuild(id).then(setBuild).catch(() => {});
      }
      if (event.type === "done") {
        getBuild(id).then(setBuild).catch(() => {});
        setLiveStep(null);
        setCurrentFile(null);
        setStreamingFile(null);
        setStreamingContent("");
      }
    });
    sseCleanupRef.current = cleanup;

    return () => { cleanup(); sseCleanupRef.current = null; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, build?.status]);

  // Fetch project files
  useEffect(() => {
    if (!id || !build) return;
    const shouldFetch = build.status === "coding" || build.status === "reviewing"
      || build.status === "deploying" || build.status === "deployed";
    if (!shouldFetch) return;

    const fetchFiles = () => {
      getBuildFiles(id)
        .then((data) => {
          setProjectFiles(data.files);
          const paths = Object.keys(data.files);
          if (paths.length > 0 && !selectedFile) {
            setSelectedFile(paths[paths.length - 1]);
          }
        })
        .catch(() => {})
        .finally(() => setFilesLoading(false));
    };

    setFilesLoading(true);
    fetchFiles();

    if (ACTIVE_STATUSES.has(build.status)) {
      filesIntervalRef.current = setInterval(fetchFiles, 4000);
    }

    return () => {
      if (filesIntervalRef.current) {
        clearInterval(filesIntervalRef.current);
        filesIntervalRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, build?.status]);

  // Fetch version chain
  useEffect(() => {
    if (!id || !build || build.status !== "deployed") return;
    getBuildChain(id).then(setVersionChain).catch(() => {});
  }, [id, build]);

  const refreshPreview = useCallback(() => {
    setPreviewKey((k) => k + 1);
  }, []);

  return {
    build,
    loadError,
    projectFiles,
    selectedFile,
    setSelectedFile,
    filesLoading,
    versionChain,
    liveStep,
    currentFile,
    streamingFile,
    streamingContent,
    previewKey,
    refreshPreview,
  };
}
