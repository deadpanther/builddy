"""Forensic analyst -- GLM 5.1 agent that performs repo autopsy"""
import json
import uuid
import asyncio
import subprocess
import os
from datetime import datetime
from openai import AsyncOpenAI
from config import settings
from agent.tools import TOOLS
from agent.executor import ToolExecutor

SYSTEM_PROMPT = """You are Dr. Autopsy, a forensic code analyst. You perform death analysis on software projects.

Your job is to examine a GitHub repository and determine WHY it died (or is dying). You are thorough,
methodical, and relentless in your investigation -- like a forensic pathologist performing an autopsy.

## Investigation Protocol

### Phase 1: Scene Examination (Ingestion)
- List all files to understand project structure
- Get commit frequency to see activity patterns
- Get contributors to understand team dynamics
- Check recent git log for signs of decline

### Phase 2: Deep Forensic Analysis
- Read key source files (entry points, config, README, tests)
- Examine commit messages for sentiment changes, urgency, frustration
- Analyze issues for unresolved bugs, feature creep, community frustration
- Check PR patterns for rejected contributions, contributor churn
- Search for TODOs, FIXMEs, HACKs -- signs of technical debt
- Look for abandoned features, commented-out code, dead code paths
- Analyze code complexity trends

### Phase 3: Autopsy Report
Synthesize all evidence into a structured report:

1. **cause_of_death**: The PRIMARY reason this project died. Be specific and cite evidence.
   Examples: "Abandoned by sole maintainer after burnout", "Unresolved critical bugs eroded user trust",
   "Architecture became unmaintainable due to scope creep", "Funding ran out", "Core dependency broke"

2. **contributing_factors**: 3-5 secondary factors that accelerated the death

3. **timeline**: List of key events chronologically. Each entry has:
   - date: YYYY-MM-DD format
   - event: What happened
   - severity: "critical", "warning", "info"
   - evidence: Supporting evidence

4. **fatal_commits**: 2-5 specific commits that were turning points. Each has:
   - hash: Commit hash
   - date: Date
   - message: Commit message
   - why_fatal: Why this commit was a turning point

5. **findings**: Detailed forensic analysis sections covering:
   - Architecture assessment
   - Code quality trajectory
   - Community health
   - Technical debt accumulation
   - Dependency management
   - Testing practices

6. **lessons_learned**: 5-8 actionable lessons other developers can learn

Be dramatic but accurate. Use forensic terminology. Cite specific evidence (file names, commit hashes, dates).
If the repo is not actually dead, say so but still analyze its health risks.

When you have gathered enough evidence, call the final_report function with all your findings.
"""

FINAL_REPORT_TOOL = {
    "type": "function",
    "function": {
        "name": "final_report",
        "description": "Submit the final autopsy report with all findings.",
        "parameters": {
            "type": "object",
            "properties": {
                "cause_of_death": {"type": "string", "description": "Primary cause of death"},
                "contributing_factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of contributing factors"
                },
                "timeline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string"},
                            "event": {"type": "string"},
                            "severity": {"type": "string"},
                            "evidence": {"type": "string"}
                        }
                    }
                },
                "fatal_commits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "hash": {"type": "string"},
                            "date": {"type": "string"},
                            "message": {"type": "string"},
                            "why_fatal": {"type": "string"}
                        }
                    }
                },
                "findings": {
                    "type": "object",
                    "description": "Detailed analysis sections"
                },
                "lessons_learned": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["cause_of_death", "contributing_factors", "timeline", "lessons_learned"]
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
        """Clone the repo for analysis"""
        repo_name = self.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        self.repo_path = os.path.join(settings.CLONE_DIR, f"{self.autopsy_id}-{repo_name}")
        os.makedirs(settings.CLONE_DIR, exist_ok=True)

        if os.path.exists(self.repo_path):
            subprocess.run(["rm", "-rf", self.repo_path], timeout=30)

        if progress_callback:
            await progress_callback("cloning", f"Cloning {self.repo_url}...")

        result = subprocess.run(
            ["git", "clone", self.repo_url, self.repo_path],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            raise Exception(f"Clone failed: {result.stderr[:500]}")

        self.executor = ToolExecutor(self.repo_path, self.repo_url)

        if progress_callback:
            await progress_callback("cloning", "Repository cloned successfully. Beginning forensic examination...")

    async def analyze(self, progress_callback=None):
        """Run the full forensic analysis using GLM 5.1"""
        # Add initial context
        self.messages.append({
            "role": "user",
            "content": f"""Perform a full autopsy on this repository: {self.repo_url}

Begin with Phase 1: Scene Examination. Use the tools to examine the repo thoroughly.
After gathering evidence, proceed to Phase 2 and Phase 3.

End by calling final_report with your complete findings. Be thorough -- this is a forensic investigation."""
        })

        report = None
        steps = 0
        nudge_count = 0

        while steps < settings.MAX_ANALYSIS_STEPS:
            steps += 1
            try:
                response = await self.client.chat.completions.create(
                    model=settings.GLM_MODEL,
                    messages=self.messages,
                    tools=self.all_tools,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=8192,
                )
            except Exception as e:
                if progress_callback:
                    await progress_callback("error", f"GLM API error: {str(e)[:200]}")
                break

            choice = response.choices[0]
            assistant_msg = choice.message

            # Add assistant response to conversation (GLM-5.1 content may be empty;
            # reasoning lives in reasoning_content but that field is not forwarded to the API)
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

            # If no tool calls, nudge the model back to using tools.
            # GLM-5.1 always returns empty content (reasoning goes to reasoning_content),
            # so we cannot rely on content length to decide whether to nudge.
            if not assistant_msg.tool_calls:
                if nudge_count < 3:
                    nudge_count += 1
                    self.messages.append({
                        "role": "user",
                        "content": "Continue your investigation using the available tools. When done, call final_report."
                    })
                    continue
                break

            # Process tool calls
            tool_responses = []
            for tc in assistant_msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError as e:
                    # GLM truncated the arguments JSON (hit max_tokens mid-generation)
                    tool_responses.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"Error: arguments JSON was truncated and could not be parsed. Use shorter arguments."
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
        """Generate a formal death certificate from the report"""
        repo_name = self.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        return {
            "certificate_number": self.autopsy_id[:8].upper(),
            "repository": repo_name,
            "repository_url": self.repo_url,
            "date_of_birth": report.get("timeline", [{}])[0].get("date", "Unknown") if report.get("timeline") else "Unknown",
            "date_of_death": report.get("timeline", [{}])[-1].get("date", "Unknown") if report.get("timeline") else "Unknown",
            "cause_of_death": report.get("cause_of_death", "Unknown"),
            "contributing_factors": report.get("contributing_factors", []),
            "examining_pathologist": "Dr. GLM 5.1",
            "date_of_examination": datetime.utcnow().isoformat(),
            "findings_summary": report.get("findings", {}),
            "lessons": report.get("lessons_learned", [])
        }
