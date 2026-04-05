"""Tool executor -- runs git commands and reads repo files"""
import subprocess
import os
import json
from typing import Optional

class ToolExecutor:
    def __init__(self, repo_path: str, repo_url: str):
        self.repo_path = repo_path
        self.repo_url = repo_url
        # Extract owner/repo from URL
        parts = repo_url.rstrip("/").split("/")
        self.owner = parts[-2] if len(parts) >= 2 else ""
        self.repo = parts[-1].replace(".git", "") if len(parts) >= 1 else ""

    def _run_git(self, *args, cwd=None) -> str:
        cmd = ["git"] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or self.repo_path, timeout=30)
        return result.stdout[:8000] if result.returncode == 0 else f"Error: {result.stderr[:500]}"

    def _run_gh(self, *args) -> str:
        cmd = ["gh"] + list(args) + ["--repo", f"{self.owner}/{self.repo}", "--limit", "30", "--json", "title,state,createdAt,closedAt,body,comments"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout[:8000] if result.returncode == 0 else f"gh not available or error: {result.stderr[:300]}"

    def list_files(self, path_prefix: str = "", extension: str = "") -> str:
        cmd = f"find . -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/venv/*' -not -path '*/__pycache__/*'"
        if path_prefix:
            cmd += f" -path './{path_prefix}*'"
        if extension:
            cmd += f" -name '*{extension}'"
        cmd += " | head -200"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.repo_path, timeout=10)
        files = result.stdout.strip()
        if not files:
            return "No files found"
        # Add file sizes
        lines = files.split("\n")
        output = []
        for f in lines[:200]:
            full = os.path.join(self.repo_path, f.lstrip("./"))
            try:
                size = os.path.getsize(full)
                output.append(f"{f} ({size} bytes)")
            except:
                output.append(f)
        return "\n".join(output)

    def read_file(self, path: str, lines: int = 200) -> str:
        full = os.path.join(self.repo_path, path)
        if not os.path.exists(full):
            return f"File not found: {path}"
        try:
            with open(full, 'r', errors='replace') as f:
                content = f.read()
            lines_list = content.split("\n")
            if len(lines_list) > lines:
                return "\n".join(lines_list[:lines]) + f"\n... ({len(lines_list)} total lines)"
            return content[:8000]
        except Exception as e:
            return f"Error reading file: {e}"

    def git_log(self, count: int = 50, author: str = "", after: str = "", before: str = "") -> str:
        args = ["log", f"--max-count={count}", "--pretty=format:%h | %ai | %an | %s", "--stat"]
        if author:
            args.append(f"--author={author}")
        if after:
            args.append(f"--after={after}")
        if before:
            args.append(f"--before={before}")
        return self._run_git(*args)[:8000]

    def git_blame(self, path: str) -> str:
        return self._run_git("blame", "-w", "-M", path)[:6000]

    def git_diff(self, commit: str) -> str:
        return self._run_git("show", "--stat", "--patch", commit)[:8000]

    def list_issues(self, state: str = "all", count: int = 30) -> str:
        cmd = ["gh", "issue", "list", "--repo", f"{self.owner}/{self.repo}",
               "--state", state, "--limit", str(count),
               "--json", "title,state,createdAt,closedAt,body,comments"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return f"Could not fetch issues: {result.stderr[:300]}"
        try:
            issues = json.loads(result.stdout)
            lines = []
            for i in issues[:30]:
                c = len(i.get("comments", []))
                lines.append(f"- [{i['state'].upper()}] {i['title']} (created: {i['createdAt'][:10]}, comments: {c})")
                if i.get("body"):
                    lines.append(f"  Body: {i['body'][:200]}")
            return "\n".join(lines) if lines else "No issues found"
        except:
            return result.stdout[:4000]

    def list_pull_requests(self, state: str = "all", count: int = 20) -> str:
        cmd = ["gh", "pr", "list", "--repo", f"{self.owner}/{self.repo}",
               "--state", state, "--limit", str(count),
               "--json", "title,state,createdAt,closedAt,mergedAt,comments,reviewDecision"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return f"Could not fetch PRs: {result.stderr[:300]}"
        try:
            prs = json.loads(result.stdout)
            lines = []
            for p in prs[:20]:
                merged = "MERGED" if p.get("mergedAt") else p["state"].upper()
                c = len(p.get("comments", []))
                lines.append(f"- [{merged}] {p['title']} (created: {p['createdAt'][:10]}, comments: {c})")
            return "\n".join(lines) if lines else "No PRs found"
        except:
            return result.stdout[:4000]

    def get_contributors(self) -> str:
        result = self._run_git("shortlog", "-sn", "--all")
        if not result.strip() or result.startswith("Error"):
            return "Could not get contributors"
        return result[:3000]

    def analyze_complexity(self, paths: list) -> str:
        output = []
        for p in paths[:20]:
            full = os.path.join(self.repo_path, p)
            if not os.path.exists(full):
                continue
            try:
                with open(full, 'r', errors='replace') as f:
                    content = f.read()
                lines = content.split("\n")
                funcs = content.count("def ") + content.count("function ") + content.count("const ")
                todos = content.lower().count("todo") + content.lower().count("hack") + content.lower().count("fixme")
                output.append(f"{p}: {len(lines)} lines, ~{funcs} functions, {todos} TODOs/hacks")
            except:
                pass
        return "\n".join(output) if output else "Could not analyze"

    def search_code(self, pattern: str, file_type: str = "") -> str:
        cmd = ["grep", "-rn", "-E", pattern, "."]
        if file_type:
            cmd = ["grep", "-rn", "--include", f"*.{file_type}", "-E", pattern, "."]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.repo_path, timeout=15)
        if result.returncode != 0:
            return f"No matches for '{pattern}'"
        lines = result.stdout.strip().split("\n")[:50]
        return "\n".join(lines)

    def get_commit_frequency(self) -> str:
        result = self._run_git("log", "--format=%ai", "--all")
        if not result.strip():
            return "No commits found"
        # Parse into monthly buckets
        from collections import Counter
        months = Counter()
        for line in result.strip().split("\n"):
            if line.strip():
                try:
                    month = line.strip()[:7]  # YYYY-MM
                    months[month] += 1
                except:
                    pass
        lines = [f"{m}: {'#' * min(c, 50)} ({c} commits)" for m, c in sorted(months.items())]
        return "\n".join(lines) if lines else "No commit data"

    def execute(self, tool_name: str, arguments: dict) -> str:
        """Dispatch a tool call by name"""
        dispatch = {
            "list_files": lambda: self.list_files(**arguments),
            "read_file": lambda: self.read_file(**arguments),
            "git_log": lambda: self.git_log(**arguments),
            "git_blame": lambda: self.git_blame(**arguments),
            "git_diff": lambda: self.git_diff(**arguments),
            "list_issues": lambda: self.list_issues(**arguments),
            "list_pull_requests": lambda: self.list_pull_requests(**arguments),
            "get_contributors": lambda: self.get_contributors(**arguments),
            "analyze_complexity": lambda: self.analyze_complexity(**arguments),
            "search_code": lambda: self.search_code(**arguments),
            "get_commit_frequency": lambda: self.get_commit_frequency(**arguments),
        }
        handler = dispatch.get(tool_name)
        if not handler:
            return f"Unknown tool: {tool_name}"
        try:
            return handler()
        except Exception as e:
            return f"Tool error: {e}"
