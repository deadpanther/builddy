# Builddy Feature Roadmap

## Goal

Identify and prioritize features to make Builddy a more robust, impressive, and marketable AI app builder.

---

## Current State

**What works:**
- Multi-step agent pipeline: Parse → Plan → Code → QA → Polish → Visual Validate → Deploy
- Simple single-file apps (HTML + Tailwind + JS)
- Fullstack multi-file apps (React + Node + SQLite)
- Modify pipeline for iterative changes
- Real-time build progress UI
- Gallery of deployed apps
- Twitter/X integration for mention-to-build
- Code Autopsy side project

**Tech stack:**
- Backend: FastAPI, SQLModel, GLM-4/5, Playwright (visual validation)
- Frontend: Next.js 14, Tailwind CSS, Auth0
- Test coverage: 71% (need 80%)

---

## Feature Proposals

### Tier 1: High Impact, Medium Effort (Do Next)

#### 1. Wire Autopilot + Test Generator into Live Pipeline

**Current gap:** `autopilot.py` and `test_gen.py` exist but aren't called by the pipeline.

**Implementation:**
```python
# After visual_validate in run_pipeline():
# Run autopilot fix loop if errors detected
code, iterations = await autopilot_fix_loop(code, on_iteration=lambda i, e, s: _add_step(build_id, f"Autopilot fix {i}: {e} errors"))

# Generate test suite after deploy
tests = await generate_tests(code, app_name=parsed.get("app_name", "App"))
```

**Files to change:**
- `agent/pipeline.py` - integrate autopilot and test_gen
- `agent/prompts.py` - add test gen prompts
- `services/deployer.py` - deploy test files alongside app

**Validation:**
- E2E test: Build app → verify autopilot runs → verify tests.html generated
- Unit tests for autopilot integration

**Estimated effort:** 4-6 hours

---

#### 2. One-Click Deploy to Railway/Render

**Current gap:** Apps only run locally. Users can't share their creations.

**Implementation:**
- `services/cloud_deploy.py` already exists with Railway API integration
- Add "Deploy to Cloud" button on build page
- Create GitHub repo → push code → trigger Railway deploy
- Show deploy status and live URL

**Files to change:**
- `routers/builds.py` - add `/deploy` endpoint
- `services/cloud_deploy.py` - complete Railway integration
- `frontend/src/app/build/[id]/page.tsx` - add deploy button
- `frontend/src/components/DeployButton.tsx` - new component

**Validation:**
- E2E test: Build → Deploy → verify live URL works
- Mock Railway API in tests

**Estimated effort:** 6-8 hours

---

#### 3. Split the 1,004-Line Build Page

**Current gap:** `page.tsx` is 1,003 lines — unmaintainable.

**Implementation:**
```
frontend/src/app/build/[id]/
├── page.tsx (main container, 150 lines)
├── components/
│   ├── BuildHeader.tsx
│   ├── BuildProgress.tsx
│   ├── CodePreview.tsx
│   ├── AppPreview.tsx
│   ├── ModifyInput.tsx
│   ├── StepTimeline.tsx
│   └── BuildActions.tsx
└── hooks/
    ├── useBuild.ts
    ├── useEventStream.ts
    └── useModify.ts
```

**Files to change:**
- `frontend/src/app/build/[id]/page.tsx` - split into components
- Create 7 new component files
- Create 3 new hook files

**Validation:**
- All existing tests pass
- Visual regression check (build page looks same)

**Estimated effort:** 3-4 hours

---

### Tier 2: High Impact, Higher Effort

#### 4. Visual Pipeline Designer

**Current gap:** Users can't customize the agent pipeline.

**Implementation:**
- Drag-and-drop pipeline builder
- Choose which agents to run: PRD, Design, QA, Polish, Autopilot, Test Gen
- Configure agent parameters (temperature, max tokens)
- Save pipeline templates

**Files to change:**
- `frontend/src/app/pipeline-designer/` - new page
- `frontend/src/components/PipelineDesigner.tsx` - DnD interface
- `backend/routers/pipelines.py` - CRUD for pipeline configs
- `backend/models/pipeline.py` - new model
- `backend/agent/pipeline.py` - accept config parameter

**Estimated effort:** 16-24 hours

---

#### 5. Prompt Version Control & A/B Testing

**Current gap:** Prompts are hardcoded. Can't iterate or compare.

**Implementation:**
- Store prompts in database with versioning
- A/B test different prompt variants
- Track which prompts produce better outputs
- Rollback to previous versions

**Files to change:**
- `backend/models/prompt_version.py` - new model
- `backend/routers/prompts.py` - CRUD + stats
- `backend/agent/prompts.py` - load from DB instead of hardcoded
- `frontend/src/app/prompts/` - prompt management UI

**Estimated effort:** 12-16 hours

---

#### 6. Better Error Messages & Recovery

**Current gap:** Errors are cryptic. Users don't know what went wrong.

**Implementation:**
- Categorize error types: API, Parse, Code, Deploy
- Generate user-friendly error messages with GLM
- Suggest fixes: "Try simplifying your prompt" or "Add more details"
- Auto-retry with adjusted parameters

**Files to change:**
- `backend/agent/error_recovery.py` - new module
- `backend/agent/pipeline.py` - catch and enrich errors
- `frontend/src/components/ErrorDisplay.tsx` - better error UI

**Estimated effort:** 8-12 hours

---

### Tier 3: Nice-to-Have Enhancements

#### 7. App Templates Gallery

**Description:** Pre-built app templates users can fork and customize.

**Examples:**
- Todo app with dark mode
- Pomodoro timer
- Expense tracker
- Quiz app

**Estimated effort:** 4-6 hours

---

#### 8. Collaboration Features

**Description:** Share builds, add comments, collaborate on modifications.

**Implementation:**
- Public/private builds
- Share links with view/edit permissions
- Comment thread on builds
- Activity feed

**Estimated effort:** 16-24 hours

---

#### 9. Mobile App (React Native)

**Description:** Build apps on mobile, push notifications when complete.

**Estimated effort:** 40+ hours

---

#### 10. API for Developers

**Description:** REST API for programmatic app generation.

**Implementation:**
- API keys
- Rate limiting per key
- Webhooks for build completion
- SDK (Python, JS)

**Estimated effort:** 8-12 hours

---

## Recommended Priority Order

1. **Wire Autopilot + Test Generator** (immediate, shows off agent capabilities)
2. **Split Build Page** (technical debt, enables faster iteration)
3. **One-Click Deploy** (key feature for demo, makes apps shareable)
4. **Better Error Messages** (UX improvement)
5. **Visual Pipeline Designer** (platform feature)
6. **Prompt Version Control** (developer platform)

---

## Quick Wins (Can do in parallel)

- Add `alt` props to images (fix lint warnings)
- Replace `<img>` with Next.js `<Image>` (performance)
- Fix Pydantic deprecation warning in `BuildResponse`
- Add more test coverage (need 9% more for 80%)

---

## Open Questions

1. Should we support more deploy targets (Vercel, Netlify, Fly.io)?
2. Should autopilot be opt-in or always-on?
3. Should test generation be mandatory or optional?
4. How to handle billing for cloud deployments?
5. Should we add authentication for saved pipelines?

---

## Files Likely to Change

### Backend
- `agent/pipeline.py` - main integration point
- `agent/autopilot.py` - needs testing
- `agent/test_gen.py` - needs testing
- `routers/builds.py` - new endpoints
- `services/cloud_deploy.py` - complete Railway integration

### Frontend
- `app/build/[id]/page.tsx` - split into components
- New: `components/DeployButton.tsx`
- New: `components/ErrorDisplay.tsx`
- New: `hooks/useBuild.ts`

### Tests
- `tests/test_pipeline.py` - integration tests
- `tests/test_autopilot.py` - already exists
- `tests/test_test_gen.py` - already exists
- E2E tests for deploy flow
