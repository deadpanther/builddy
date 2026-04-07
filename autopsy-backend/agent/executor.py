"""Tool executor — runs git commands and analyzes repo files for forensic investigation."""

import subprocess
import os
import json
import re
import fnmatch as fnmatch_mod
from collections import Counter


class ToolExecutor:
    def __init__(self, repo_path: str, repo_url: str):
        self.repo_path = repo_path
        self.repo_url = repo_url
        parts = repo_url.rstrip("/").split("/")
        self.owner = parts[-2] if len(parts) >= 2 else ""
        self.repo = parts[-1].replace(".git", "") if len(parts) >= 1 else ""

    _EXCLUDE_DIRS = {'.git', 'node_modules', 'venv', '__pycache__', '.venv', 'dist', '.next'}

    def _walk_files(self, extensions=None, patterns=None, prefix='', limit=200):
        """Walk repo files safely without shell. Returns relative paths."""
        found = []
        for root, dirs, filenames in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self._EXCLUDE_DIRS]
            for f in filenames:
                rel = os.path.relpath(os.path.join(root, f), self.repo_path)
                if prefix and not rel.startswith(prefix):
                    continue
                if extensions and not any(f.endswith(e) for e in extensions):
                    continue
                if patterns and not any(fnmatch_mod.fnmatch(f, p) for p in patterns):
                    continue
                found.append(rel)
                if len(found) >= limit:
                    return found
        return found

    def _run(self, cmd, timeout=30) -> str:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=self.repo_path, timeout=timeout,
        )
        return result.stdout[:8000] if result.returncode == 0 else f"Error: {result.stderr[:500]}"

    def _run_git(self, *args) -> str:
        return self._run(["git"] + list(args))

    # ── Core tools ───────────────────────────────────────────────────────────

    def list_files(self, path_prefix: str = "", extension: str = "") -> str:
        exts = [extension] if extension else None
        files = self._walk_files(extensions=exts, prefix=path_prefix, limit=200)
        files.sort()
        if not files:
            return "No files found"
        output = []
        for f in files:
            full = os.path.join(self.repo_path, f)
            try:
                size = os.path.getsize(full)
                output.append(f"./{f} ({size:,} bytes)")
            except Exception:
                output.append(f"./{f}")
        return "\n".join(output)

    def read_file(self, path: str, lines: int = 200, offset: int = 0) -> str:
        full = os.path.join(self.repo_path, path)
        if not os.path.exists(full):
            return f"File not found: {path}"
        try:
            with open(full, "r", errors="replace") as f:
                content = f.read()
            lines_list = content.split("\n")
            total = len(lines_list)
            chunk = lines_list[offset:offset + lines]
            result = "\n".join(chunk)
            if offset + lines < total:
                result += f"\n... (showing lines {offset+1}-{offset+len(chunk)} of {total} total)"
            elif offset > 0:
                result = f"(lines {offset+1}-{offset+len(chunk)} of {total})\n" + result
            return result[:8000]
        except Exception as e:
            return f"Error reading file: {e}"

    def git_log(self, count: int = 50, author: str = "", after: str = "", before: str = "", path: str = "") -> str:
        args = ["log", f"--max-count={count}", "--pretty=format:%h | %ai | %an | %s", "--stat"]
        if author:
            args.append(f"--author={author}")
        if after:
            args.append(f"--after={after}")
        if before:
            args.append(f"--before={before}")
        if path:
            args += ["--", path]
        return self._run_git(*args)[:8000]

    def git_blame(self, path: str) -> str:
        return self._run_git("blame", "-w", "-M", "--line-porcelain", path)[:6000]

    def git_diff(self, commit: str) -> str:
        return self._run_git("show", "--stat", "--patch", commit)[:8000]

    def list_issues(self, state: str = "all", count: int = 30) -> str:
        cmd = ["gh", "issue", "list", "--repo", f"{self.owner}/{self.repo}",
               "--state", state, "--limit", str(count),
               "--json", "title,state,createdAt,closedAt,body,comments,labels"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return f"Could not fetch issues (gh CLI may not be available): {result.stderr[:300]}"
        try:
            issues = json.loads(result.stdout)
            lines = []
            for i in issues[:30]:
                c = len(i.get("comments", []))
                labels = ", ".join(l.get("name", "") for l in i.get("labels", []))
                label_str = f" [{labels}]" if labels else ""
                lines.append(f"- [{i['state'].upper()}]{label_str} {i['title']} (created: {i['createdAt'][:10]}, comments: {c})")
                if i.get("body"):
                    lines.append(f"  Body: {i['body'][:300]}")
            return "\n".join(lines) if lines else "No issues found"
        except Exception:
            return result.stdout[:4000]

    def list_pull_requests(self, state: str = "all", count: int = 20) -> str:
        cmd = ["gh", "pr", "list", "--repo", f"{self.owner}/{self.repo}",
               "--state", state, "--limit", str(count),
               "--json", "title,state,createdAt,closedAt,mergedAt,comments,reviewDecision,author"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return f"Could not fetch PRs: {result.stderr[:300]}"
        try:
            prs = json.loads(result.stdout)
            lines = []
            for p in prs[:20]:
                merged = "MERGED" if p.get("mergedAt") else p["state"].upper()
                c = len(p.get("comments", []))
                author = p.get("author", {}).get("login", "unknown")
                review = p.get("reviewDecision", "none")
                lines.append(f"- [{merged}] {p['title']} by @{author} (created: {p['createdAt'][:10]}, comments: {c}, review: {review})")
            return "\n".join(lines) if lines else "No PRs found"
        except Exception:
            return result.stdout[:4000]

    def get_contributors(self) -> str:
        result = self._run_git("shortlog", "-sn", "--all")
        if not result.strip() or result.startswith("Error"):
            return "Could not get contributors"
        return result[:3000]

    # ── Deep analysis tools ──────────────────────────────────────────────────

    def analyze_complexity(self, paths: list) -> str:
        output = []
        for p in paths[:20]:
            full = os.path.join(self.repo_path, p)
            if not os.path.exists(full):
                continue
            try:
                with open(full, "r", errors="replace") as f:
                    content = f.read()
                lines = content.split("\n")
                total_lines = len(lines)
                blank = sum(1 for l in lines if not l.strip())
                comments = sum(1 for l in lines if l.strip().startswith(("#", "//", "/*", "*", "'''", '"""')))
                code_lines = total_lines - blank - comments

                # Count definitions
                funcs = len(re.findall(r"\bdef\s+\w+|function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\(|=>\s*{", content))
                classes = len(re.findall(r"\bclass\s+\w+", content))

                # Code smells
                todos = len(re.findall(r"(?i)\bTODO\b", content))
                fixmes = len(re.findall(r"(?i)\bFIXME\b", content))
                hacks = len(re.findall(r"(?i)\bHACK\b", content))
                noqa = len(re.findall(r"noqa|eslint-disable|type:\s*ignore|@ts-ignore", content))

                # Long functions (rough: >50 lines between def/function)
                long_funcs = 0
                in_func = False
                func_lines = 0
                for line in lines:
                    if re.match(r"\s*(def |function |async function |const \w+ = )", line):
                        if in_func and func_lines > 50:
                            long_funcs += 1
                        in_func = True
                        func_lines = 0
                    elif in_func:
                        func_lines += 1
                if in_func and func_lines > 50:
                    long_funcs += 1

                # Max nesting depth
                max_indent = 0
                for line in lines:
                    if line.strip():
                        indent = len(line) - len(line.lstrip())
                        max_indent = max(max_indent, indent // 4)

                report = f"""{p}:
  Lines: {total_lines} total ({code_lines} code, {blank} blank, {comments} comments)
  Structure: {funcs} functions, {classes} classes
  Smells: {todos} TODOs, {fixmes} FIXMEs, {hacks} HACKs, {noqa} lint suppresions
  Long functions (>50 lines): {long_funcs}
  Max nesting depth: {max_indent} levels"""
                output.append(report)
            except Exception:
                pass
        return "\n\n".join(output) if output else "Could not analyze"

    def search_code(self, pattern: str, file_type: str = "") -> str:
        cmd = ["grep", "-rn", "-E", pattern, "."]
        if file_type:
            cmd = ["grep", "-rn", "--include", f"*.{file_type}", "-E", pattern, "."]
        # Exclude common non-source dirs
        cmd += ["--exclude-dir=node_modules", "--exclude-dir=.git", "--exclude-dir=venv", "--exclude-dir=dist", "--exclude-dir=.next"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.repo_path, timeout=15)
        if result.returncode != 0:
            return f"No matches for '{pattern}'"
        lines = result.stdout.strip().split("\n")[:50]
        return f"Found {len(lines)} matches:\n" + "\n".join(lines)

    def get_commit_frequency(self) -> str:
        result = self._run_git("log", "--format=%ai", "--all")
        if not result.strip():
            return "No commits found"
        months = Counter()
        for line in result.strip().split("\n"):
            if line.strip():
                try:
                    months[line.strip()[:7]] += 1
                except Exception:
                    pass
        lines = []
        sorted_months = sorted(months.items())
        for m, c in sorted_months:
            bar = "#" * min(c, 50)
            lines.append(f"{m}: {bar} ({c} commits)")

        # Add gap analysis
        if len(sorted_months) >= 2:
            all_months = [m for m, _ in sorted_months]
            first, last = all_months[0], all_months[-1]
            lines.append(f"\nActive period: {first} to {last}")
            lines.append(f"Total active months: {len(all_months)}")
            total = sum(c for _, c in sorted_months)
            lines.append(f"Average: {total / len(all_months):.1f} commits/month")

        return "\n".join(lines)

    def check_dependencies(self) -> str:
        """Analyze dependency files for health signals."""
        dep_files = {
            "package.json": self._analyze_npm,
            "requirements.txt": self._analyze_pip_requirements,
            "pyproject.toml": self._analyze_pyproject,
            "Cargo.toml": self._analyze_generic_deps,
            "go.mod": self._analyze_generic_deps,
            "Gemfile": self._analyze_generic_deps,
        }
        output = []
        for filename, analyzer in dep_files.items():
            full = os.path.join(self.repo_path, filename)
            if os.path.exists(full):
                try:
                    with open(full, "r", errors="replace") as f:
                        content = f.read()
                    result = analyzer(content, filename)
                    output.append(result)
                except Exception as e:
                    output.append(f"{filename}: Error analyzing — {e}")

        # Check for lock files
        lock_files = ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock", "uv.lock", "Cargo.lock"]
        found_locks = [f for f in lock_files if os.path.exists(os.path.join(self.repo_path, f))]
        if found_locks:
            output.append(f"Lock files present: {', '.join(found_locks)} (dependency versions are pinned)")
        else:
            output.append("WARNING: No lock files found — dependency versions may drift")

        return "\n\n".join(output) if output else "No dependency files found"

    def _analyze_npm(self, content: str, filename: str) -> str:
        try:
            pkg = json.loads(content)
            deps = pkg.get("dependencies", {})
            dev_deps = pkg.get("devDependencies", {})
            scripts = pkg.get("scripts", {})

            # Check pinning
            unpinned = [k for k, v in {**deps, **dev_deps}.items() if v.startswith("^") or v.startswith("~")]

            lines = [f"package.json:"]
            lines.append(f"  Dependencies: {len(deps)} runtime, {len(dev_deps)} dev")
            lines.append(f"  Scripts: {', '.join(scripts.keys())}")
            if unpinned:
                lines.append(f"  Unpinned (^/~): {len(unpinned)} — risk of breaking updates")
            if "test" not in scripts and "jest" not in scripts:
                lines.append(f"  WARNING: No test script found")
            return "\n".join(lines)
        except Exception:
            return f"package.json: Could not parse JSON"

    def _analyze_pip_requirements(self, content: str, filename: str) -> str:
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        pinned = sum(1 for l in lines if "==" in l)
        unpinned = sum(1 for l in lines if ">=" in l or l.strip().isalpha())
        return f"requirements.txt:\n  Total deps: {len(lines)}\n  Pinned (==): {pinned}\n  Unpinned (>=): {unpinned}"

    def _analyze_pyproject(self, content: str, filename: str) -> str:
        deps = re.findall(r'"([^"]+)"', content)
        return f"pyproject.toml:\n  Dependencies found: {len(deps)}\n  Content preview: {content[:500]}"

    def _analyze_generic_deps(self, content: str, filename: str) -> str:
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
        return f"{filename}:\n  Lines: {len(lines)}\n  Preview: {content[:500]}"

    def check_tests(self) -> str:
        """Analyze test infrastructure."""
        output = []

        # Find test files
        test_patterns = ["test_*.py", "*_test.py", "*.test.js", "*.test.ts", "*.test.tsx",
                         "*.spec.js", "*.spec.ts", "*.spec.tsx", "*_test.go", "*_test.rs"]
        test_files = []
        matched = self._walk_files(patterns=test_patterns, limit=50)
        test_files = [f"./{f}" for f in matched]

        if test_files:
            output.append(f"Test files found: {len(test_files)}")
            for f in test_files[:20]:
                output.append(f"  {f}")
        else:
            output.append("WARNING: No test files found — zero test coverage")

        # Check for test config
        test_configs = ["jest.config.js", "jest.config.ts", "pytest.ini", "setup.cfg", "pyproject.toml",
                        ".mocharc.yml", "vitest.config.ts", "cypress.config.js", ".github/workflows"]
        found_configs = []
        for cfg in test_configs:
            full = os.path.join(self.repo_path, cfg)
            if os.path.exists(full):
                found_configs.append(cfg)
        if found_configs:
            output.append(f"Test config: {', '.join(found_configs)}")

        # Check CI/CD
        ci_dirs = [".github/workflows", ".circleci", ".travis.yml", "Jenkinsfile", ".gitlab-ci.yml"]
        found_ci = [d for d in ci_dirs if os.path.exists(os.path.join(self.repo_path, d))]
        if found_ci:
            output.append(f"CI/CD: {', '.join(found_ci)}")
        else:
            output.append("WARNING: No CI/CD configuration found")

        # Source-to-test ratio
        all_src = self._walk_files(extensions=['.py', '.js', '.ts', '.tsx'], limit=5000)
        src_files = [f for f in all_src if 'test' not in f.lower() and 'spec' not in f.lower()]
        src_count = len(src_files)
        if src_count > 0 and test_files:
            ratio = len(test_files) / src_count
            output.append(f"Test-to-source ratio: {ratio:.2f} ({len(test_files)} test files / {src_count} source files)")
            if ratio < 0.1:
                output.append("CRITICAL: Very low test coverage — less than 10% of source files have tests")

        return "\n".join(output) if output else "Could not analyze test infrastructure"

    def get_file_history(self, path: str) -> str:
        """Get the change history of a specific file."""
        log = self._run_git("log", "--follow", "--pretty=format:%h | %ai | %an | %s", "--", path)
        if not log.strip() or log.startswith("Error"):
            return f"No history found for {path}"

        commits = log.strip().split("\n")
        output = [f"File: {path}", f"Total changes: {len(commits)} commits", ""]
        for c in commits[:30]:
            output.append(c)

        # Get first and last modification
        if len(commits) >= 2:
            output.append(f"\nFirst created: {commits[-1].split('|')[1].strip()[:10]}")
            output.append(f"Last modified: {commits[0].split('|')[1].strip()[:10]}")

        # Check churn (files changed too often = instability)
        if len(commits) > 20:
            output.append(f"\nWARNING: High churn — {len(commits)} changes indicates instability")

        return "\n".join(output)

    def get_repo_health(self) -> str:
        """Get overall repository health metrics."""
        output = []

        # Total commits
        total = self._run_git("rev-list", "--count", "HEAD").strip()
        output.append(f"Total commits: {total}")

        # First and last commit dates
        first = self._run_git("log", "--reverse", "--format=%ai", "-1").strip()[:10]
        last = self._run_git("log", "--format=%ai", "-1").strip()[:10]
        output.append(f"First commit: {first}")
        output.append(f"Last commit: {last}")

        # Days since last commit
        import datetime
        try:
            last_date = datetime.datetime.strptime(last, "%Y-%m-%d")
            days_idle = (datetime.datetime.now() - last_date).days
            output.append(f"Days since last commit: {days_idle}")
            if days_idle > 365:
                output.append("CRITICAL: Project appears abandoned (>1 year since last commit)")
            elif days_idle > 180:
                output.append("WARNING: Project may be stale (>6 months since last commit)")
            elif days_idle > 90:
                output.append("NOTE: Activity has slowed (>3 months since last commit)")
        except Exception:
            pass

        # File count
        file_count = len(self._walk_files(limit=10000))
        output.append(f"Files in repo: {file_count}")

        # Lines of code (approximate)
        code_exts = ['.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.rb']
        code_files = self._walk_files(extensions=code_exts, limit=5000)
        total_loc = 0
        for cf in code_files:
            try:
                with open(os.path.join(self.repo_path, cf), 'r', errors='replace') as fh:
                    total_loc += sum(1 for _ in fh)
            except Exception:
                pass
        output.append(f"Lines of code: {total_loc} total")

        # Contributors count
        contrib = self._run_git("shortlog", "-sn", "--all").strip()
        num_contributors = len(contrib.split("\n")) if contrib and not contrib.startswith("Error") else 0
        output.append(f"Contributors: {num_contributors}")

        # Bus factor
        if contrib and not contrib.startswith("Error"):
            lines = contrib.strip().split("\n")
            if lines:
                counts = []
                for line in lines:
                    parts = line.strip().split("\t")
                    if parts and parts[0].strip().isdigit():
                        counts.append(int(parts[0].strip()))
                if counts:
                    total_commits = sum(counts)
                    top = counts[0]
                    bus_factor_pct = (top / total_commits * 100) if total_commits > 0 else 0
                    output.append(f"Bus factor: Top contributor has {bus_factor_pct:.0f}% of all commits")
                    if bus_factor_pct > 80:
                        output.append("CRITICAL: Single point of failure — one person owns >80% of commits")

        # Branches
        branches = self._run_git("branch", "-a").strip()
        branch_count = len(branches.split("\n")) if branches else 0
        output.append(f"Branches: {branch_count}")

        # Tags/releases
        tags = self._run_git("tag", "-l").strip()
        tag_count = len(tags.split("\n")) if tags.strip() else 0
        output.append(f"Tags/releases: {tag_count}")
        if tag_count == 0:
            output.append("WARNING: No releases/tags — no versioning strategy")

        return "\n".join(output)

    def analyze_commit_messages(self, count: int = 50) -> str:
        """Analyze commit message patterns and sentiment."""
        result = self._run_git("log", f"--max-count={count}", "--pretty=format:%s")
        if not result.strip() or result.startswith("Error"):
            return "No commits to analyze"

        messages = result.strip().split("\n")
        output = [f"Analyzing {len(messages)} commit messages:", ""]

        # Message length analysis
        lengths = [len(m) for m in messages]
        avg_len = sum(lengths) / len(lengths) if lengths else 0
        one_word = sum(1 for m in messages if len(m.split()) <= 1)
        output.append(f"Average message length: {avg_len:.0f} chars")
        output.append(f"One-word messages: {one_word} ({one_word/len(messages)*100:.0f}%)")

        # Pattern detection
        patterns = {
            "fix/bug": r"(?i)\b(fix|bug|patch|hotfix)\b",
            "wip/temp": r"(?i)\b(wip|temp|tmp|todo|hack)\b",
            "frustration": r"(?i)\b(fuck|shit|damn|ugh|argh|wtf|ffs|finally|stupid|broken)\b",
            "rush/panic": r"(?i)\b(urgent|asap|quick fix|emergency|hotfix|critical|breaking)\b",
            "revert": r"(?i)\b(revert|rollback|undo)\b",
            "refactor": r"(?i)\b(refactor|cleanup|clean up|reorganize|restructure)\b",
            "feature": r"(?i)\b(add|implement|feature|new|create|introduce)\b",
            "docs": r"(?i)\b(docs|readme|documentation|comment)\b",
            "merge/conflict": r"(?i)\b(merge|conflict|resolve)\b",
        }

        for label, pattern in patterns.items():
            matches = [m for m in messages if re.search(pattern, m)]
            if matches:
                pct = len(matches) / len(messages) * 100
                output.append(f"\n{label.upper()} ({len(matches)}, {pct:.0f}%):")
                for m in matches[:5]:
                    output.append(f"  - {m[:100]}")

        # Conventional commits check
        conventional = sum(1 for m in messages if re.match(r"^(feat|fix|chore|docs|style|refactor|test|ci|perf|build)(\(.+\))?:", m))
        if conventional > len(messages) * 0.3:
            output.append(f"\nConventional commits: {conventional}/{len(messages)} — good practice")
        elif conventional == 0:
            output.append(f"\nNo conventional commits used — unstructured history")

        return "\n".join(output)

    # ── Dispatcher ───────────────────────────────────────────────────────────

    def execute(self, tool_name: str, arguments: dict) -> str:
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
            "check_dependencies": lambda: self.check_dependencies(),
            "check_tests": lambda: self.check_tests(),
            "get_file_history": lambda: self.get_file_history(**arguments),
            "get_repo_health": lambda: self.get_repo_health(),
            "analyze_commit_messages": lambda: self.analyze_commit_messages(**arguments),
        }
        handler = dispatch.get(tool_name)
        if not handler:
            return f"Unknown tool: {tool_name}"
        try:
            return handler()
        except Exception as e:
            return f"Tool error: {e}"
