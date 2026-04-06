# Builddy Differentiators — Full Vision Design

**Goal:** Transform Builddy from an AI app generator into an AI development platform with iterative building, live full-stack preview, app remix ecosystem, and one-click cloud deployment.

**Priority Order:**
1. Iterative Development Loop (biggest moat)
2. Live Full-Stack Preview + Data Seeding
3. App Remix Ecosystem (network effects)
4. Real Deployment Pipeline (polish)

---

## 1. Iterative Development Loop

### Concept
Instead of single-shot generation, Builddy becomes a conversation. Users progressively build up their app across multiple turns: "add auth", "add a settings page", "connect a weather API" — and Builddy intelligently updates only affected files.

### Smart Modification Pipeline

```
User modification request
    |
Impact Analyzer (GLM 5.1 with thinking)
    -> reads full manifest + all existing files
    -> outputs: { files_to_create, files_to_modify, files_unchanged }
    |
Targeted File Generation (only changed files)
    -> new files: generated with full context
    -> modified files: original + modification + context
    -> unchanged: carried forward as-is
    |
Integration Review (reviews changed files against unchanged)
    |
Deploy + Zip (merged project)
```

### New Prompts
- `IMPACT_SYSTEM` — Analyzes modification request against manifest, determines which files need creation/modification/no change
- `MODIFY_FILE_SYSTEM` — Modifies a single existing file given the change request and full project context

### Conversation Thread UI
Build detail page gets a version history sidebar:
```
v1: Task Manager (original)
  v2: + Added user authentication
    v3: + Added settings page
      v4: + Dark mode theme
```
Each version clickable, previewable, downloadable. Users can branch from any version.

### Key Advantage
Most AI builders regenerate everything or only handle single files. The impact analyzer understands the full project graph — GLM 5.1's long-horizon reasoning handles this. Single-shot generators can't replicate this because they have no memory of what exists.

---

## 2. Live Full-Stack Preview + Data Seeding

### Concept
After deploying standard/fullstack builds, actually run the Express + SQLite backend so users can test real CRUD, auth flows, and data persistence — not just static HTML.

### How It Works
1. `npm install` in deployed directory
2. Generate + run `init-data.js` to seed SQLite with 10-20 realistic records
3. Start Express on dynamic port (9000+)
4. Reverse-proxy `/apps/{build_id}/api/*` to running Express process
5. Kill idle servers after 30 min, restart on next visit, max ~20 concurrent

### New Components
- `SEED_SYSTEM` prompt — generates realistic seed data from manifest + schema
- Process manager — starts/stops/monitors Express processes per build
- Reverse proxy config in FastAPI — proxy API requests to Express
- `init-data.js` generation step in pipeline

### Safety
- No network egress from sandboxed processes
- No filesystem access outside app directory
- CPU/memory limits via Node's --max-old-space-size
- Idle timeout cleanup

### User Experience
Click "Open Live App" and see a fully working app with real populated data. Create tasks, sign up, log in, toggle settings — all real, all persisted.

---

## 3. App Remix Ecosystem

### Concept
Every deployed app is forkable. Gallery becomes a marketplace of starting points.

### How Remixing Works
1. User browses gallery, finds an app to build on
2. Clicks "Remix this app", enters modification description
3. Builddy creates new build with parent_build_id, copies all files
4. Runs impact analysis -> targeted modification pipeline
5. Remix ships as independent project

### Gallery Upgrades
- "Remixed X times" counter per app
- "Remix" button with text input
- Trending section (most-remixed)
- Tags/categories: productivity, games, dashboards, social, tools

### Why This Creates a Moat
- Network effects: more users = more apps = better templates = more users
- Quality ratchet: popular apps get improved through remixing
- Speed advantage: remixing is 10x faster than building from scratch

---

## 4. Real Deployment Pipeline

### Concept
One-click deploy from Builddy to Railway, Render, or a Builddy subdomain.

### Two Tiers
**Tier 1: Builddy-hosted (free)**
- Current `/apps/{build_id}/` with live backend
- Ephemeral (servers sleep after 30 min)

**Tier 2: Cloud deploy**
- Railway: push to temp GitHub repo, trigger deploy via API
- Render: same flow
- Builddy subdomains: `myapp.builddy.app` with longer timeouts

### New Fields
- `deploy_provider`: railway | render | builddy | null
- `deploy_external_url`: the live production URL
- `deploy_status`: pending | deploying | live | failed

---

## Implementation Phases

### Phase A: Iterative Development Loop
- New prompts: IMPACT_SYSTEM, MODIFY_FILE_SYSTEM
- New pipeline: run_modify_fullstack_pipeline
- Update modify endpoint to handle multi-file builds
- Version history UI component
- Branch-from-any-version support

### Phase B: Live Full-Stack Preview
- Process manager service
- Reverse proxy in FastAPI
- SEED_SYSTEM prompt + init-data.js generation
- npm install automation
- Idle cleanup / resource limits

### Phase C: App Remix Ecosystem
- Remix endpoint (fork + modify in one step)
- Gallery UI upgrades (remix button, counters, trending, tags)
- Category/tag system for builds

### Phase D: Cloud Deployment
- GitHub API integration (create repo, push files)
- Railway / Render deploy API integration
- Builddy subdomain proxy
- Deploy status tracking UI
