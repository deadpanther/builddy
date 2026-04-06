# Multi-File Full-Stack App Generation

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform Builddy from generating single-file HTML apps to producing complete, deployable multi-file full-stack projects (frontend + backend + deployment config), with zip download and hosted preview.

**Architecture:** Three-tier complexity classification (simple/standard/fullstack) determines the generation pipeline. Simple apps use the existing single-file path. Standard/fullstack apps go through a new multi-phase pipeline: classify -> plan manifest -> generate files sequentially (backend-first) -> integration review -> deploy + zip. Generated projects use Express.js + SQLite backend, vanilla HTML/CSS/JS + Tailwind CDN frontend, with Dockerfile for deployment.

**Tech Stack:** Python/FastAPI (Builddy backend), GLM 5.1 (generation), Next.js/TypeScript (Builddy frontend), Express.js + SQLite (generated apps)

---

## Phase 1: Backend — New Prompts & Complexity Classifier

### Task 1: Add new fields to Build model

**Files:**
- Modify: `backend/models.py:13-34`

**Step 1: Add complexity, file_manifest, generated_files, zip_url, tech_stack fields**

```python
# Add after line 28 (build_type field):
complexity: Optional[str] = Field(default="simple")  # simple, standard, fullstack
file_manifest: Optional[str] = Field(default=None)  # JSON: [{path, purpose, dependencies}]
generated_files: Optional[str] = Field(default=None)  # JSON: {filepath: content}
zip_url: Optional[str] = Field(default=None)  # /downloads/{build_id}/project.zip
tech_stack: Optional[str] = Field(default=None)  # JSON: {frontend, backend, db, ...}
```

**Step 2: Add DB migration for new columns**

In `backend/database.py`, add to `_migrate_new_columns()`:

```python
("builds", "complexity", "TEXT DEFAULT 'simple'"),
("builds", "file_manifest", "TEXT"),
("builds", "generated_files", "TEXT"),
("builds", "zip_url", "TEXT"),
("builds", "tech_stack", "TEXT"),
```

**Step 3: Update BuildResponse in builds router**

In `backend/routers/builds.py`, add to BuildResponse class:

```python
complexity: Optional[str] = "simple"
file_manifest: Optional[str] = None
generated_files: Optional[str] = None
zip_url: Optional[str] = None
tech_stack: Optional[str] = None
```

---

### Task 2: Write new prompts for multi-file generation

**Files:**
- Modify: `backend/agent/prompts.py`

Add these new prompt constants:

1. `CLASSIFY_SYSTEM` — Classifies request into simple/standard/fullstack, outputs JSON with complexity + reasoning
2. `MANIFEST_SYSTEM` — Plans full file manifest with paths, purposes, API routes, DB tables
3. `FILEGEN_SYSTEM` — Generates a single file given manifest + previously generated files as context
4. `INTEGRATION_SYSTEM` — Reviews all files together, fixes broken imports/routes/references
5. `DOCKERFILE_TEMPLATE` — Template for Dockerfile (string format, not LLM-generated)
6. `DOCKER_COMPOSE_TEMPLATE` — Template for docker-compose.yml
7. `PACKAGE_JSON_TEMPLATE` — Template for package.json
8. `README_TEMPLATE` — Template for README.md with deploy instructions

---

### Task 3: Implement the multi-file pipeline

**Files:**
- Modify: `backend/agent/pipeline.py`

Add new functions:

1. `classify_complexity(build_id, prompt)` — Uses CLASSIFY_SYSTEM to determine tier
2. `plan_manifest(build_id, prompt, complexity)` — Uses MANIFEST_SYSTEM to create file list
3. `generate_file(build_id, manifest, file_entry, generated_so_far)` — Uses FILEGEN_SYSTEM per file
4. `generate_all_files(build_id, prompt, manifest)` — Iterates manifest, calls generate_file sequentially
5. `integration_review(build_id, all_files)` — Uses INTEGRATION_SYSTEM to fix cross-file issues
6. `generate_deployment_files(manifest, all_files)` — Creates Dockerfile, docker-compose, package.json, README from templates
7. `run_fullstack_pipeline(build_id)` — Full pipeline: classify -> plan -> generate -> integrate -> review -> deploy + zip

Update `run_pipeline()` to:
- Call classify_complexity first
- If simple: use existing single-file path
- If standard/fullstack: call run_fullstack_pipeline

---

### Task 4: Update deployer for multi-file projects

**Files:**
- Modify: `backend/services/deployer.py`

Add:

1. `deploy_project(build_id, files_dict)` — Writes all files to `deployed/{build_id}/`, returns deploy URL
2. `create_project_zip(build_id, files_dict)` — Creates zip archive at `deployed/{build_id}/project.zip`, returns download URL
3. Keep existing `deploy_html()` for simple tier backward compatibility

---

### Task 5: Add download and files API endpoints

**Files:**
- Modify: `backend/routers/builds.py`

Add endpoints:

1. `GET /api/builds/{id}/download` — Returns zip file as streaming response
2. `GET /api/builds/{id}/files` — Returns JSON list of all generated files with content
3. `GET /api/builds/{id}/files/{path:path}` — Returns single file content

---

### Task 6: Mount zip downloads in main.py

**Files:**
- Modify: `backend/main.py`

- Update static file mounting to serve zips from deployed directory

---

## Phase 2: Frontend — File Explorer & Download UI

### Task 7: Update TypeScript types

**Files:**
- Modify: `frontend/src/lib/types.ts`

Add to Build interface:
```typescript
complexity?: "simple" | "standard" | "fullstack";
file_manifest?: string;  // JSON
generated_files?: string;  // JSON
zip_url?: string;
tech_stack?: string;  // JSON
```

Add new types:
```typescript
interface FileManifestEntry {
  path: string;
  purpose: string;
  generates_api?: string[];
  uses_api?: string[];
  tables?: string[];
  dependencies?: string[];
}

interface TechStack {
  frontend: string;
  backend: string;
  database: string;
  deployment: string;
}
```

---

### Task 8: Update API client

**Files:**
- Modify: `frontend/src/lib/api.ts`

Add:
```typescript
export function getDownloadUrl(buildId: string): string
export async function getBuildFiles(buildId: string): Promise<Record<string, string>>
```

---

### Task 9: Create FileExplorer component

**Files:**
- Create: `frontend/src/components/FileExplorer.tsx`

Tree view with:
- Folder expand/collapse
- File icons by type (.js, .html, .css, .json, .md)
- Click to select file
- Selected file shown in CodePreview
- File size indicators

---

### Task 10: Update BuildCard with complexity badges

**Files:**
- Modify: `frontend/src/components/BuildCard.tsx`

- Show complexity tier badge (Simple/Standard/Full-stack)
- Show tech stack tags when available
- Add download quick-action for deployed multi-file builds

---

### Task 11: Update build detail page

**Files:**
- Modify: `frontend/src/app/build/[id]/page.tsx`

Major changes:
- Add "Files" tab alongside "Preview" and "Code"
- Files tab shows FileExplorer on left + CodePreview on right
- Add "Download Project" button in header
- Show complexity tier badge
- Show tech stack in metadata section
- For multi-file builds, "Code" tab shows file explorer instead of single code block

---

### Task 12: Update AgentSteps for new pipeline stages

**Files:**
- Modify: `frontend/src/components/AgentSteps.tsx`

Add new pipeline steps:
- "Classifying" — determining complexity
- "Planning Files" — creating manifest
- "Generating" — file-by-file generation (show progress: 3/8 files)
- "Integrating" — cross-file review
- "Packaging" — creating zip

---

### Task 13: Update gallery to show complexity & download

**Files:**
- Modify: `backend/routers/gallery.py`
- Modify: `frontend/src/app/gallery/page.tsx` (if exists)

Add complexity, tech_stack, zip_url to gallery response.
