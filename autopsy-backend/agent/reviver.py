"""Revival planner — GLM agent that creates actionable resurrection plans from autopsy findings."""

import json
from openai import AsyncOpenAI
from config import settings


SYSTEM_PROMPT = """You are **Dr. Revive**, a legendary software resurrection specialist. You've brought hundreds of dead repositories back to life, turning abandoned codebases into thriving projects.

You've received a forensic autopsy report for a code repository. Your job is to create a detailed, actionable revival plan that addresses every pathology found AND proposes mind-blowing new features that would make this project genuinely exciting again.

Your style:
- **Optimistic but realistic** — every repo can be saved, but be honest about the effort required
- **Extremely specific** — "fix the tests" is useless. "Add pytest fixtures for the database layer in db/models.py and create integration tests for the /api/users endpoint" is useful
- **Prioritized** — what to do first, second, third. Quick wins before deep surgery
- **Creative and bold** — for feature suggestions, think about what would make developers EXCITED to contribute again. What would make this repo go viral on Hacker News?

## Your Approach

1. Analyze the autopsy findings carefully — every issue mentioned is a clue to what needs fixing
2. Create a phased revival plan, starting with emergency stabilization and ending with growth
3. Identify quick wins that can show immediate progress and build momentum
4. Suggest 5-8 genuinely innovative features that leverage the project's existing strengths
5. Be specific about files, modules, tools, and libraries to use

## Feature Ideas Should Be

- **Genuinely innovative** — not "add dark mode" but something that makes people say "whoa"
- **Technically grounded** — explain HOW to build it, not just what it does
- **Strategically smart** — features that attract contributors, users, or both
- **Proportional** — mix of small delights and ambitious moonshots

Call `revival_plan` with your complete resurrection protocol when ready."""


REVIVAL_PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "revival_plan",
        "description": "Submit the complete revival plan and feature suggestions. Call this with your full resurrection protocol.",
        "parameters": {
            "type": "object",
            "properties": {
                "executive_summary": {
                    "type": "string",
                    "description": "One compelling paragraph: what's wrong, what's the path forward, and why this repo deserves to live again."
                },
                "priority": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Overall urgency of revival. Critical = repo is actively dangerous (security holes). Low = minor improvements needed."
                },
                "phases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "phase_number": {"type": "integer"},
                            "title": {"type": "string", "description": "Phase name, e.g. 'Emergency Stabilization'"},
                            "description": {"type": "string", "description": "What this phase accomplishes"},
                            "estimated_effort": {"type": "string", "description": "e.g. '1-2 weeks', '2-3 days'"},
                            "actions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "action": {"type": "string", "description": "Specific thing to do"},
                                        "target": {"type": "string", "description": "Which file, module, or system area"},
                                        "rationale": {"type": "string", "description": "Why — tied back to an autopsy finding"},
                                        "difficulty": {"type": "string", "enum": ["easy", "moderate", "hard"]}
                                    },
                                    "required": ["action", "target", "rationale", "difficulty"]
                                }
                            }
                        },
                        "required": ["phase_number", "title", "description", "estimated_effort", "actions"]
                    },
                    "description": "3-5 ordered phases of revival, from emergency fixes to growth initiatives"
                },
                "quick_wins": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "5-10 things fixable in under a day that show immediate progress"
                },
                "tech_debt_payoff_order": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ordered list of technical debt to address, highest ROI first"
                },
                "architecture_recommendations": {
                    "type": "string",
                    "description": "Specific architectural changes to improve the system design"
                },
                "testing_strategy": {
                    "type": "string",
                    "description": "Concrete plan for achieving good test coverage — which frameworks, which modules first"
                },
                "dependency_overhaul": {
                    "type": "string",
                    "description": "Which dependencies to update, replace, or remove and why"
                },
                "security_fixes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific security issues to fix, ordered by severity"
                },
                "community_revival_plan": {
                    "type": "string",
                    "description": "How to attract contributors, improve docs, make the project welcoming"
                },
                "features": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Catchy feature name"},
                            "description": {"type": "string", "description": "What it does and why users would love it"},
                            "why_this_changes_everything": {"type": "string", "description": "The 'wow factor' — why this makes the project special"},
                            "technical_approach": {"type": "string", "description": "How to build it — specific libraries, APIs, architecture"},
                            "impact": {"type": "string", "enum": ["transformative", "high", "moderate"]},
                            "effort": {"type": "string", "enum": ["small", "medium", "large"]}
                        },
                        "required": ["title", "description", "why_this_changes_everything", "technical_approach", "impact", "effort"]
                    },
                    "description": "5-8 innovative feature ideas that would make this project exciting again"
                }
            },
            "required": ["executive_summary", "priority", "phases", "quick_wins", "features"]
        }
    }
}


class RevivalPlanner:
    def __init__(self, autopsy_id: str, autopsy_data: dict):
        self.autopsy_id = autopsy_id
        self.autopsy_data = autopsy_data
        self.client = AsyncOpenAI(
            api_key=settings.GLM_API_KEY,
            base_url=settings.GLM_BASE_URL,
        )

    def _build_autopsy_context(self) -> str:
        """Format the autopsy findings as context for the revival agent."""
        d = self.autopsy_data
        sections = [
            f"# Autopsy Report: {d.get('repo_name', 'Unknown')}",
            f"**Repository:** {d.get('repo_url', 'Unknown')}",
            f"**Health Score:** {d.get('health_score', 'N/A')} / 100",
            f"**Cause of Death:** {d.get('cause_of_death', 'Unknown')}",
            f"**Prognosis:** {d.get('prognosis', 'N/A')}",
        ]

        factors = d.get("contributing_factors", [])
        if factors:
            sections.append("\n## Contributing Factors")
            for f in factors:
                sections.append(f"- {f}")

        findings = d.get("findings", {})
        if findings:
            sections.append("\n## Forensic Findings")
            for key, value in findings.items():
                label = key.replace("_", " ").title()
                sections.append(f"\n### {label}\n{value}")

        lessons = d.get("lessons_learned", [])
        if lessons:
            sections.append("\n## Lessons Learned")
            for i, lesson in enumerate(lessons, 1):
                sections.append(f"{i}. {lesson}")

        timeline = d.get("timeline", [])
        if timeline:
            sections.append("\n## Timeline of Decline")
            for evt in timeline:
                date = evt.get("date", "?")
                event = evt.get("event", "")
                severity = evt.get("severity", "info")
                sections.append(f"- [{severity.upper()}] {date}: {event}")

        fatal = d.get("fatal_commits", [])
        if fatal:
            sections.append("\n## Fatal Commits")
            for c in fatal:
                sections.append(f"- {c.get('hash', '?')[:8]} ({c.get('date', '?')}): {c.get('message', '')} — {c.get('why_fatal', '')}")

        return "\n".join(sections)

    async def generate(self, progress_callback=None):
        """Generate the revival plan using GLM."""
        if progress_callback:
            await progress_callback("reviving", "Dr. Revive is analyzing the autopsy findings...")

        context = self._build_autopsy_context()

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""Here is the complete autopsy report for this repository. Create a detailed revival plan that addresses every issue found and suggests mind-blowing features to make it awesome again.

{context}

Analyze these findings carefully, then call `revival_plan` with your complete resurrection protocol. Be extremely specific — file names, library names, concrete steps."""
            }
        ]

        if progress_callback:
            await progress_callback("reviving", "Formulating resurrection protocol...")

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = await self.client.chat.completions.create(
                    model=settings.GLM_MODEL,
                    messages=messages,
                    tools=[REVIVAL_PLAN_TOOL],
                    tool_choice={"type": "function", "function": {"name": "revival_plan"}},
                    temperature=0.4,
                    max_tokens=16384,
                )

                choice = response.choices[0]
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        if tc.function.name == "revival_plan":
                            try:
                                result = json.loads(tc.function.arguments)
                            except json.JSONDecodeError:
                                if attempt < max_attempts - 1:
                                    if progress_callback:
                                        await progress_callback("reviving", f"Response was truncated, retrying (attempt {attempt + 2}/{max_attempts})...")
                                    messages.append({
                                        "role": "assistant",
                                        "content": "",
                                        "tool_calls": [tc.model_dump()],
                                    })
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tc.id,
                                        "content": "Error: your JSON was truncated. Please call revival_plan again with complete JSON. Use shorter descriptions if needed."
                                    })
                                    continue
                                raise

                            if progress_callback:
                                await progress_callback("reviving", "Resurrection protocol complete!")

                            # Split features out of the plan
                            features = result.pop("features", [])
                            return result, features

                # No tool call — retry with nudge
                if attempt < max_attempts - 1:
                    messages.append({
                        "role": "assistant",
                        "content": choice.message.content or "",
                    })
                    messages.append({
                        "role": "user",
                        "content": "Please call the `revival_plan` tool with your complete findings now."
                    })
                    if progress_callback:
                        await progress_callback("reviving", "Refining the plan...")

            except json.JSONDecodeError:
                if attempt == max_attempts - 1:
                    raise Exception("Failed to parse revival plan after multiple attempts")
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                if progress_callback:
                    await progress_callback("reviving", f"Retrying after error: {str(e)[:100]}")

        raise Exception("Failed to generate revival plan after maximum attempts")
