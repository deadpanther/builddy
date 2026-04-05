"""Forensic analyst — GLM agent that performs deep repo autopsy with structured investigation."""

import json
import subprocess
import os
from datetime import datetime
from openai import AsyncOpenAI
from config import settings
from agent.tools import TOOLS
from agent.executor import ToolExecutor

SYSTEM_PROMPT = """You are **Dr. Autopsy**, a legendary forensic code pathologist. You perform meticulous post-mortem examinations on software repositories to determine cause of death, contributing pathologies, and lessons for the living.

Your analysis style is:
- **Dramatic but evidence-based** — every claim backed by specific files, commits, or metrics
- **Forensic vocabulary** — "time of death", "toxicology" (dependencies), "trauma patterns" (code smells)
- **Brutally honest** — no sugar-coating. If the code is bad, say why. If the project was doomed from birth, explain.
- **Deeply technical** — you understand architecture patterns, anti-patterns, and why projects actually fail

## Investigation Protocol (Follow this EXACTLY)

### Phase 1: Scene Examination (3-5 tool calls)
1. `get_repo_health` — vital signs: commits, contributors, activity, bus factor
2. `list_files` — project structure, understand the anatomy
3. `get_commit_frequency` — activity timeline, detect decline patterns
4. `get_contributors` — team dynamics, contributor drop-off

### Phase 2: Deep Forensic Analysis (10-15 tool calls)
5. `read_file` README.md — understand what the project claims to be
6. `read_file` on entry points (main.py, index.js, server.py, app.py, etc.)
7. `check_dependencies` — dependency health, version pinning, bloat
8. `check_tests` — test infrastructure, coverage gaps
9. `analyze_commit_messages` — developer sentiment, rush patterns, frustration markers
10. `search_code` for "TODO|FIXME|HACK|XXX" — technical debt markers
11. `search_code` for "deprecated|obsolete|legacy|workaround" — decay signals
12. `analyze_complexity` on the largest source files — code quality trajectory
13. `git_log` for recent commits — was there a final burst of activity or slow decline?
14. `git_diff` on suspicious commits — what did the fatal changes actually do?
15. `get_file_history` on the most-changed files — hotspot analysis
16. `list_issues` — community health, unresolved bugs
17. `list_pull_requests` — contribution patterns, rejected PRs

### Phase 3: Synthesize & Report
After gathering evidence, call `final_report` with your complete forensic findings.

## Forensic Report Requirements

Your `findings` object MUST include ALL of these sections with detailed analysis:

### architecture
Assess the system architecture: monolith vs microservices, separation of concerns, coupling, cohesion. Is it well-structured or a big ball of mud? Cite specific files and patterns.

### code_quality
Code quality trajectory: naming conventions, function sizes, nesting depth, DRY violations, dead code. Include specific file:line examples of the worst offenders.

### technical_debt
Technical debt accumulation: TODO count, hack markers, lint suppressions, workarounds, deprecated patterns. Quantify the debt load with evidence.

### dependency_health
Dependency management: are versions pinned? Any known vulnerable or abandoned dependencies? Over-reliance on unmaintained packages? Lock file discipline.

### testing_practices
Testing rigor: test coverage, test types (unit/integration/e2e), CI/CD pipeline, test-to-source ratio. If there are no tests, this is a critical finding.

### community_health
Community dynamics: contributor count and distribution, bus factor, issue response time, PR review culture, communication patterns in commits.

### security_posture
Security assessment: hardcoded secrets, exposed API keys, SQL injection vectors, XSS potential, missing auth checks, .env handling.

### scalability_risks
Scalability concerns: single-threaded bottlenecks, missing caching, N+1 queries, unbounded data structures, missing pagination.

## Death Classification

Classify the death as one of:
- **HOMICIDE** — killed by external forces (funding cut, company pivot, acqui-hire)
- **SUICIDE** — self-inflicted (scope creep, rewrite-from-scratch, perfectionism paralysis)
- **NATURAL CAUSES** — gradual decline (tech debt accumulation, slow contributor attrition)
- **ACCIDENT** — sudden death (catastrophic bug, data loss, security breach)
- **STILL ALIVE** — not dead yet, but list health risks and prognosis

Include the classification in your cause_of_death.

IMPORTANT: Be thorough in your investigation but efficient with your tool calls. You have a limited number of steps. Prioritize the most revealing tools first. When you have enough evidence, call final_report immediately — do not keep investigating indefinitely.
"""

FINAL_REPORT_TOOL = {
    "type": "function",
    "function": {
        "name": "final_report",
        "description": "Submit the final autopsy report. Call this when you have gathered enough evidence. Include ALL required sections.",
        "parameters": {
            "type": "object",
            "properties": {
                "cause_of_death": {
                    "type": "string",
                    "description": "Primary cause of death with death classification (HOMICIDE/SUICIDE/NATURAL CAUSES/ACCIDENT/STILL ALIVE). Be specific and dramatic."
                },
                "contributing_factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-7 secondary factors that contributed to death. Each should be a specific, evidence-backed statement."
                },
                "timeline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "YYYY-MM-DD format"},
                            "event": {"type": "string", "description": "What happened — be specific"},
                            "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                            "evidence": {"type": "string", "description": "Cite specific commits, files, or metrics"}
                        },
                        "required": ["date", "event", "severity", "evidence"]
                    },
                    "description": "6-15 chronological events that tell the story of this project's life and death"
                },
                "fatal_commits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "hash": {"type": "string"},
                            "date": {"type": "string"},
                            "message": {"type": "string"},
                            "why_fatal": {"type": "string", "description": "Detailed explanation of why this commit was a turning point"}
                        },
                        "required": ["hash", "date", "message", "why_fatal"]
                    },
                    "description": "3-5 specific commits that were turning points"
                },
                "findings": {
                    "type": "object",
                    "description": "Detailed forensic findings organized by category",
                    "properties": {
                        "architecture": {"type": "string", "description": "Architecture assessment with specific file references"},
                        "code_quality": {"type": "string", "description": "Code quality analysis with examples"},
                        "technical_debt": {"type": "string", "description": "Technical debt quantification"},
                        "dependency_health": {"type": "string", "description": "Dependency analysis"},
                        "testing_practices": {"type": "string", "description": "Test infrastructure assessment"},
                        "community_health": {"type": "string", "description": "Community and contributor analysis"},
                        "security_posture": {"type": "string", "description": "Security assessment"},
                        "scalability_risks": {"type": "string", "description": "Scalability concerns"}
                    }
                },
                "health_score": {
                    "type": "integer",
                    "description": "Overall health score from 0 (dead) to 100 (thriving)"
                },
                "prognosis": {
                    "type": "string",
                    "description": "If still alive: prognosis for survival. If dead: what it would take to resurrect. Be specific."
                },
                "lessons_learned": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "5-10 actionable lessons with specific advice, not generic platitudes"
                }
            },
            "required": ["cause_of_death", "contributing_factors", "timeline", "findings", "health_score", "lessons_learned"]
        }
    }
}


class ForensicAnalyst:
    def __init__(self, autopsy_id: str, repo_url: str):
        self.autopsy_id = autopsy_id
        self.repo_url = repo_url
        self.repo_path = ""
        self.client = AsyncOpenAI(
            api_key=settings.GLM_API_KEY,
            base_url=settings.GLM_BASE_URL,
        )
        self.executor = None
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.evidence_log = []
        self.all_tools = TOOLS + [FINAL_REPORT_TOOL]

    async def clone_repo(self, progress_callback=None):
        """Clone the repo for analysis."""
        repo_name = self.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        self.repo_path = os.path.join(settings.CLONE_DIR, f"{self.autopsy_id}-{repo_name}")
        os.makedirs(settings.CLONE_DIR, exist_ok=True)

        if os.path.exists(self.repo_path):
            subprocess.run(["rm", "-rf", self.repo_path], timeout=30)

        if progress_callback:
            await progress_callback("cloning", f"Cloning {self.repo_url}...")

        result = subprocess.run(
            ["git", "clone", "--depth=500", self.repo_url, self.repo_path],
            capture_output=True, text=True, timeout=120,
        )

        if result.returncode != 0:
            raise Exception(f"Clone failed: {result.stderr[:500]}")

        self.executor = ToolExecutor(self.repo_path, self.repo_url)

        if progress_callback:
            await progress_callback("cloning", "Repository cloned successfully. Beginning forensic examination...")

    async def analyze(self, progress_callback=None):
        """Run the full forensic analysis using GLM."""
        self.messages.append({
            "role": "user",
            "content": f"""Perform a full forensic autopsy on: {self.repo_url}

Follow the Investigation Protocol exactly:
1. Phase 1: Scene Examination — get vital signs, structure, activity patterns
2. Phase 2: Deep Analysis — read code, check dependencies, tests, commits, security
3. Phase 3: Call final_report with your complete findings

You have {settings.MAX_ANALYSIS_STEPS} investigation steps. Use them wisely — prioritize the most revealing tools.
Start with get_repo_health and list_files."""
        })

        report = None
        steps = 0
        nudge_count = 0

        while steps < settings.MAX_ANALYSIS_STEPS:
            steps += 1
            remaining = settings.MAX_ANALYSIS_STEPS - steps

            # Nudge when running low
            if remaining == 8:
                self.messages.append({
                    "role": "user",
                    "content": "You have 8 steps remaining. Make sure to investigate tests, dependencies, and security before wrapping up. Then call final_report."
                })
            elif remaining == 4:
                self.messages.append({
                    "role": "user",
                    "content": "4 steps remaining. Start synthesizing your evidence and prepare to call final_report with comprehensive findings."
                })
            elif remaining == 1:
                self.messages.append({
                    "role": "user",
                    "content": "FINAL STEP. Call final_report NOW with all evidence gathered. Include all 8 findings sections, health_score, prognosis, and detailed lessons_learned."
                })

            try:
                response = await self.client.chat.completions.create(
                    model=settings.GLM_MODEL,
                    messages=self.messages,
                    tools=self.all_tools,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=16384,
                )
            except Exception as e:
                if progress_callback:
                    await progress_callback("error", f"GLM API error: {str(e)[:200]}")
                break

            choice = response.choices[0]
            assistant_msg = choice.message

            # Build assistant message for conversation
            if assistant_msg.tool_calls:
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_msg.content or "",
                    "tool_calls": [tc.model_dump() for tc in assistant_msg.tool_calls],
                })
            else:
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_msg.content or "",
                })

            # No tool calls — nudge or break
            if not assistant_msg.tool_calls:
                if nudge_count < 3:
                    nudge_count += 1
                    self.messages.append({
                        "role": "user",
                        "content": "Continue investigating with the available tools. When you have enough evidence, call final_report with comprehensive findings."
                    })
                    continue
                break

            # Process tool calls
            tool_responses = []
            for tc in assistant_msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    tool_responses.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "Error: arguments JSON was truncated. Use shorter arguments or fewer parameters."
                    })
                    continue

                if fn_name == "final_report":
                    report = fn_args
                    tool_responses.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "Report submitted successfully."
                    })
                    if progress_callback:
                        await progress_callback("complete", "Autopsy complete. Generating death certificate...")
                    continue

                # Execute the tool
                evidence = f"[{fn_name}] {json.dumps(fn_args)[:100]}"
                try:
                    result = self.executor.execute(fn_name, fn_args)
                    evidence += f" -> {result[:200]}"
                    self.evidence_log.append({
                        "tool": fn_name,
                        "input": fn_args,
                        "observation": result[:500]
                    })
                except Exception as e:
                    result = f"Error: {str(e)[:200]}"
                    evidence += f" -> ERROR: {str(e)[:100]}"

                if progress_callback:
                    await progress_callback("analyzing", evidence)

                tool_responses.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result[:8000]
                })

            self.messages.extend(tool_responses)

            if report:
                break

        # Cleanup clone
        if os.path.exists(self.repo_path):
            subprocess.run(["rm", "-rf", self.repo_path], timeout=30)

        return report

    def generate_death_certificate(self, report: dict) -> dict:
        """Generate a formal death certificate from the report."""
        repo_name = self.repo_url.rstrip("/").split("/")[-1].replace(".git", "")

        # Determine classification
        cause = report.get("cause_of_death", "")
        classification = "UNDETERMINED"
        for c in ["HOMICIDE", "SUICIDE", "NATURAL CAUSES", "ACCIDENT", "STILL ALIVE"]:
            if c in cause.upper():
                classification = c
                break

        timeline = report.get("timeline", [])
        first_event = timeline[0] if timeline else {}
        last_event = timeline[-1] if timeline else {}

        return {
            "certificate_number": self.autopsy_id[:8].upper(),
            "repository": repo_name,
            "repository_url": self.repo_url,
            "classification": classification,
            "date_of_birth": first_event.get("date", "Unknown"),
            "date_of_death": last_event.get("date", "Unknown"),
            "cause_of_death": report.get("cause_of_death", "Unknown"),
            "contributing_factors": report.get("contributing_factors", []),
            "health_score": report.get("health_score", 0),
            "prognosis": report.get("prognosis", ""),
            "examining_pathologist": "Dr. GLM — Forensic Code Pathologist",
            "date_of_examination": datetime.utcnow().isoformat(),
            "findings_summary": report.get("findings", {}),
            "lessons": report.get("lessons_learned", []),
        }
