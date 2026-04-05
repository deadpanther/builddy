# Builddy

**AI-powered app builder that turns natural language prompts into deployed web apps in minutes.**

Describe what you want, and Builddy's multi-step agent pipeline — powered by GLM — plans the architecture, generates complete code, self-reviews it, and deploys a live app. Then iterate on it with follow-up modifications.

Built for the [Z.ai Build with GLM 5.1 Challenge](https://aivalley.io).

---

## What It Does

1. **You describe an app** — "Build me a pomodoro timer with dark mode"
2. **GLM plans the architecture** — Layout, features, styling, interactivity
3. **GLM generates the code** — Complete HTML/CSS/JS, no dependencies
4. **GLM self-reviews** — Catches bugs, fixes issues
5. **Builddy deploys it** — Live URL in seconds
6. **You iterate** — "Add sound effects" → GLM modifies the existing code → redeploys

Every step is visible in real-time through the agent pipeline UI.

---

## Architecture

```
User Prompt
    │
    ▼
┌─────────────────────────────────────────────┐
│  Frontend (Next.js · Port 3000)             │
│  Dashboard → Build Detail → Gallery         │
│  Real-time polling · Modify UI              │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Backend API (FastAPI · Port 8000)          │
│                                             │
│  ┌─── Agent Pipeline ────────────────────┐  │
│  │ 1. PARSE    → extract app request     │  │
│  │ 2. PLAN     → design architecture     │  │
│  │ 3. CODE     → generate HTML/CSS/JS    │  │
│  │ 4. REVIEW   → self-review & fix       │  │
│  │ 5. DEPLOY   → save & serve            │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  Modify Pipeline: existing code + change    │
│  → GLM applies modification → redeploy     │
│                                             │
│  Static Mount: /apps/{id}/ → live app       │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  GLM (Zhipu AI)                             │
│  4 LLM calls per build · 1 per modification │
│  Multi-step reasoning · Code generation     │
└─────────────────────────────────────────────┘
```

### Bonus: Code Autopsy

Feed any GitHub repo URL and GLM performs a forensic analysis — reading files, commits, issues — then issues a "death certificate" explaining why the project failed. Runs on a separate backend (port 8001).

---

## Why GLM

Builddy isn't a single API call. Each build involves **4 distinct GLM reasoning steps** that demonstrate GLM's strengths:

- **Long-horizon reasoning** — The plan step designs a full app architecture, then code generation produces a coherent implementation across HTML, CSS, and JS
- **Multi-step workflows** — Parse → Plan → Code → Review is a chained pipeline where each step builds on the previous
- **Tool use / Agent behavior** — The modify pipeline takes existing code + a natural language change request and applies targeted modifications while preserving the rest
- **Self-correction** — The review step catches and fixes its own bugs before deployment

---

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) 18+
- GLM API key from [open.bigmodel.cn](https://open.bigmodel.cn)

### 1. Clone & configure

```bash
git clone https://github.com/deadpanther/builddy.git
cd builddy

# Set up environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your GLM_API_KEY
```

### 2. Start all services (3 terminals)

**Terminal 1 — Builddy Backend (port 8000)**
```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend (port 3000)**
```bash
cd frontend
npm install
npm run dev
```

**Terminal 3 — Code Autopsy Backend (port 8001)**
```bash
cd autopsy-backend
cp ../backend/.env .env    # reuse the same GLM key
uv sync
uv run uvicorn main:app --reload --port 8001
```

### 3. Open the app

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Builddy API | http://localhost:8000/docs |
| Autopsy API | http://localhost:8001/docs |
| Deployed apps | http://localhost:8000/apps/{id}/ |

Submit a prompt on the dashboard, watch the agent pipeline work in real-time, and see your app deploy live. Then use the **Modify** input to iterate on it.

---

## Project Structure

```
builddy/
├── backend/                 # Builddy API (FastAPI)
│   ├── agent/
│   │   ├── llm.py           # GLM API client (async httpx)
│   │   ├── pipeline.py      # Build + modify pipelines
│   │   └── prompts.py       # System prompts per stage
│   ├── routers/
│   │   ├── builds.py        # Build CRUD + modify endpoint
│   │   ├── gallery.py       # Deployed apps gallery
│   │   └── twitter.py       # Twitter/X integration
│   ├── services/
│   │   ├── deployer.py      # Static HTML deployment
│   │   └── twitter.py       # Twitter API v2 client
│   ├── main.py              # FastAPI app entry
│   ├── models.py            # SQLModel schemas
│   ├── database.py          # SQLite setup
│   ├── config.py            # Pydantic settings
│   └── pyproject.toml       # uv dependencies
│
├── frontend/                # Next.js 14 App Router
│   └── src/
│       ├── app/
│       │   ├── page.tsx             # Dashboard + live feed
│       │   ├── build/[id]/page.tsx  # Build detail + modify
│       │   ├── gallery/page.tsx     # Deployed apps grid
│       │   └── autopsy/            # Code Autopsy pages
│       ├── components/
│       │   ├── AgentSteps.tsx       # Pipeline visualization
│       │   ├── BuildFeed.tsx        # Auto-refreshing feed
│       │   ├── AppPreview.tsx       # Live iframe preview
│       │   ├── CodePreview.tsx      # Code viewer
│       │   └── SubmitBuild.tsx      # Build form
│       └── lib/
│           ├── api.ts               # API client
│           └── types.ts             # TypeScript interfaces
│
├── autopsy-backend/         # Code Autopsy API (FastAPI)
│   ├── agent/               # Forensic analysis agent
│   ├── main.py              # Autopsy endpoints + WebSocket
│   └── pyproject.toml       # uv dependencies
│
└── architecture.md          # Detailed system design
```

---

## API Endpoints

### Builds
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/builds` | Create a new build from prompt |
| GET | `/api/builds` | List all builds |
| GET | `/api/builds/{id}` | Get build details |
| POST | `/api/builds/{id}/modify` | Modify an existing build |
| POST | `/api/builds/{id}/deploy` | Manually trigger deploy |

### Gallery
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/gallery` | List deployed apps |

### Twitter (requires API credentials)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/twitter/poll` | Poll for @builddy mentions |
| GET | `/api/twitter/mentions` | List recent mentions |

---

## Build Pipeline States

```
pending → planning → coding → reviewing → deploying → deployed
                                              ↘ failed
```

Each state is visible in the UI with a live pipeline visualization and step-by-step log.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | GLM via Zhipu AI API |
| Backend | FastAPI, SQLModel, SQLite, httpx |
| Frontend | Next.js 14, React 18, Tailwind CSS, Lucide icons |
| Package Manager | uv (Python), npm (Node.js) |
| Deployment | Static HTML served by FastAPI |

---

## Environment Variables

```env
# Required
GLM_API_KEY=your_key          # From open.bigmodel.cn
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
GLM_MODEL=glm-4.5

# Optional — Twitter integration
TWITTER_BEARER_TOKEN=
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=
```

---

## Team

Built for the Z.ai Builder Series · Build with GLM 5.1 Challenge

---

## License

MIT
