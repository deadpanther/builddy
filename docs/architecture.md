# Architecture

## System Overview

Builddy is a multi-agent AI app builder with three main components:

1. **Frontend** (Next.js 14) -- Dashboard, build detail, gallery, live pipeline visualization
2. **Backend** (FastAPI) -- API server, agent pipeline, deployment engine
3. **Code Autopsy** (FastAPI) -- Separate service for repo forensic analysis

---

## Agent Pipeline

The core of Builddy is a 9-stage agent pipeline that transforms a natural language prompt into a deployed web app:

```
PARSE -> PLAN -> CODE -> REVIEW -> POLISH -> VISUAL -> AUTOPILOT -> TEST_GEN -> DEPLOY
```

### Stage Details

**1. PARSE** (`agent/prompts.py: PARSE_SYSTEM`)
- Extracts: app name, description, features, tech stack, layout type
- Uses GLM-5.1 with chain-of-thought
- Output: structured JSON manifest

**2. PLAN** (`agent/prompts.py: PLAN_SYSTEM`)
- Designs: component hierarchy, color scheme, typography, data flow
- Input: parsed manifest
- Output: detailed implementation plan

**3. CODE** (`agent/pipeline.py: _generate_code`)
- Generates complete HTML/CSS/JS for simple apps
- For fullstack: generates Node.js/Express backend + React frontend
- Uses GLM-4.5 (fast model) for bulk generation
- Falls back to GLM-5.1 on failure

**4. REVIEW** (`agent/pipeline.py: _review_pass`)
- Self-review: catches bugs, accessibility issues, broken styles
- Uses GLM-5.1 for thorough analysis
- Automatically fixes identified issues

**5. POLISH** (`agent/pipeline.py: polish_pass`)
- Adds: smooth animations, dark mode support, empty states, micro-interactions
- Uses GLM-4.5 for fast iteration

**6. VISUAL VALIDATE** (`agent/pipeline.py: visual_validate`)
- Screenshots the app in a headless browser (Playwright)
- Sends screenshot + code to GLM-5V (vision model)
- Fixes visual issues: layout breaks, overflow, alignment

**7. AUTOPILOT** (`agent/autopilot.py`)
- Runs the app in a headless browser
- Detects JavaScript console errors
- Attempts fix using vision model (screenshot + errors + code)
- Falls back to text model, then fast model
- Iterates up to 3 times until clean

**8. TEST GENERATION** (`agent/test_gen.py`)
- Simple apps: generates HTML test file with inline assertions
- Fullstack apps: generates Node.js test suite (node:test + node:assert)
- Tests API endpoints, CRUD operations, validation, edge cases
- Non-blocking -- deployed alongside the app

**9. DEPLOY** (`services/deployer.py`)
- Simple apps: static HTML served from `/apps/{id}/`
- Fullstack apps: Node.js process managed by process manager
- Cloud: push to Railway or Render via API

---

## Data Model

### Build (models.py)

```
Build
+-- id: str (UUID)
+-- prompt: str
+-- app_name: str
+-- status: pending | planning | coding | reviewing | polishing | validating | autopilot | deploying | deployed | failed
+-- build_type: text | image | tweet | fullstack
+-- complexity: simple | fullstack
+-- generated_code: str (HTML for simple apps)
+-- generated_files: str (JSON dict for fullstack)
+-- deploy_url: str
+-- deploy_provider: str
+-- deploy_status: str
+-- steps: str (JSON array of pipeline steps)
+-- parent_build_id: str (for modify/remix chain)
+-- tweet_text: str
+-- created_at: datetime
+-- updated_at: datetime
```

### PromptVersion (models.py)

```
PromptVersion
+-- id: str
+-- name: str
+-- stage: str (parse | plan | code | review)
+-- system_prompt: str
+-- is_active: bool
+-- created_at: datetime
```

### Experiment (models.py)

```
Experiment
+-- id: str
+-- name: str
+-- control_version_id: str
+-- variant_version_id: str
+-- traffic_split: float (0.0-1.0)
+-- is_active: bool
+-- results: str (JSON)
+-- created_at: datetime
```

---

## SSE Streaming

Build progress is streamed via Server-Sent Events:

```
GET /api/builds/{id}/stream
```

**Event types:**
- `connected` -- initial handshake
- `step` -- pipeline stage update with message
- `status` -- build status change
- `ping` -- keepalive (every 15s)
- `done` -- terminal state (deployed/failed)

**Implementation:**
- Pub/sub via `asyncio.Queue` per subscriber
- `subscribe(build_id)` / `unsubscribe(build_id, queue)` manage queues
- Client disconnect detection via `request.is_disconnected()`

---

## Autopilot Error Recovery

The autopilot system runs a headless browser validation loop:

```
for i in range(3):  # MAX_AUTOPILOT_ITERATIONS
    1. validate_html(code) in Playwright
    2. If no errors -> done
    3. If errors -> attempt_fix(code, errors, screenshot)
       a. Try vision model (GLM-5V) with screenshot
       b. Fallback to reasoning model (GLM-5.1)
       c. Fallback to fast model (GLM-4.5)
    4. If fix == original code -> stop (no improvement)
```

Controlled by `ENABLE_AUTOPILOT` config flag.

---

## Cloud Deployment Flow

```
POST /api/builds/{id}/cloud-deploy {"provider": "railway"}
    |
    v
1. Collect project files (generated_files or generated_code)
2. deploy_to_cloud(build_id, provider, files, app_name)
   - Railway: create project -> deploy via API
   - Render: create service -> deploy via API
3. Update build record with deploy_provider, deploy_status, deploy_external_url
4. Return updated build
```

Deploy status polling:
```
GET /api/builds/{id}/deploy-status
```

---

## Modify Pipeline

```
POST /api/builds/{id}/modify {"prompt": "Add dark mode"}
    |
    v
1. Fetch original build (parent)
2. Create new Build linked via parent_build_id
3. Run modify pipeline:
   a. Send original code + modification request to GLM-5.1
   b. GLM applies targeted changes while preserving existing code
   c. Review, polish, validate, autopilot, test gen, deploy
4. New build deployed independently
```

The build chain (original -> modifications) is queryable via:
```
GET /api/builds/{id}/chain
```

---

## Twitter Integration

```
Twitter Poll (every 60s)
    |
    v
1. Search for @builddy mentions
2. For each new mention:
   a. Extract app description from tweet text
   b. Create Build (build_type="tweet")
   c. Run pipeline
   d. Reply with deployed URL
```

Requires Twitter API v2 credentials (bearer token + OAuth 1.0a).
