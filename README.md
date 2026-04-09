# Builddy

[![CI](https://github.com/deadpanther/builddy/actions/workflows/ci.yml/badge.svg)](https://github.com/deadpanther/builddy/actions/workflows/ci.yml)
[![](https://img.shields.io/badge/tests-449-brightgreen)]()
[![](https://img.shields.io/badge/coverage-80%25-green)]()
[![](https://img.shields.io/badge/license-MIT-blue)]()
[![](https://img.shields.io/badge/GLM-5.1-purple)]()
[![](https://img.shields.io/badge/Python-3.12-yellow)]()
[![](https://img.shields.io/badge/Next.js-14-black)]()

**AI-powered app builder that turns natural language into deployed web apps in minutes.**

Describe what you want, and Builddy's multi-agent pipeline -- powered by GLM -- plans the architecture, generates complete code, self-reviews it, auto-fixes runtime errors, generates tests, and deploys a live app. Then iterate with follow-up modifications.

Built for the **Z.ai Build with GLM 5.1 Challenge**.

---

## Features

- **One-prompt apps** -- "Build a pomodoro timer with dark mode" -> live URL in ~60 seconds
- **Fullstack support** -- Node.js/Express backends with database schemas and API routes
- **Autopilot error recovery** -- Headless browser detects JS errors, GLM auto-fixes them iteratively
- **Auto test generation** -- Generates and deploys test suites (HTML or Node.js) after each build
- **Visual review** -- GLM-5V screenshots the app and fixes visual issues
- **Cloud deploy** -- One-click deploy to Railway or Render
- **Twitter bot** -- Mentions @builddy with a description -> auto-builds and replies
- **Code Autopsy** -- Feed a GitHub repo URL, get a forensic "death certificate" analysis
- **Real-time streaming** -- SSE-based pipeline visualization as your app is built
- **Gallery** -- Browse and remix all deployed apps
- **449 tests, 80% coverage** -- Production-quality backend

---

## Architecture

```
User Prompt / Tweet / Screenshot
    |
    v
+------------------------------------------+
|  Frontend (Next.js 14 . Port 3000)       |
|  Dashboard / Build Detail / Gallery       |
|  Real-time SSE pipeline visualization     |
+------------------+-----------------------+
                   |
                   v
+------------------------------------------+
|  Backend API (FastAPI . Port 8000)       |
|                                          |
|  +--- Agent Pipeline -----------------+  |
|  | 1. PARSE     extract app request   |  |
|  | 2. PLAN      design architecture   |  |
|  | 3. CODE      generate HTML/CSS/JS  |  |
|  | 4. REVIEW    self-review & fix     |  |
|  | 5. POLISH    animations, dark mode |  |
|  | 6. VISUAL    screenshot -> GLM-5V  |  |
|  | 7. AUTOPILOT headless browser loop |  |
|  | 8. TEST GEN  auto test suites      |  |
|  | 9. DEPLOY    static + cloud deploy |  |
|  +------------------------------------+  |
|                                          |
|  Modify Pipeline: code + change -> GLM   |
|  Fullstack Pipeline: Node.js + Express   |
+------------------+-----------------------+
                   |
                   v
+------------------------------------------+
|  GLM (Zhipu AI)                          |
|  glm-5.1   planning, review, QA          |
|  glm-4.5   fast code generation          |
|  glm-5     fallback                      |
|  glm-5v    vision-based review           |
|  cogView-4 image generation              |
+------------------------------------------+
```

---

## Quick Start

### Option A: Local Development

**Prerequisites:** [uv](https://docs.astral.sh/uv/), Node.js 18+, GLM API key from [open.bigmodel.cn](https://open.bigmodel.cn)

```bash
git clone https://github.com/deadpanther/builddy.git
cd builddy

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env: add your GLM_API_KEY
```

**Terminal 1 -- Backend (port 8000):**
```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

**Terminal 2 -- Frontend (port 3000):**
```bash
cd frontend
npm install
npm run dev
```

**Terminal 3 -- Code Autopsy (port 8001, optional):**
```bash
cd autopsy-backend
cp ../backend/.env .env
uv sync
uv run uvicorn main:app --reload --port 8001
```

Open http://localhost:3000 and start building!

### Option B: Docker

```bash
git clone https://github.com/deadpanther/builddy.git
cd builddy

# Create .env with your keys
echo "GLM_API_KEY=your_key_here" > .env

docker compose up --build
```

### Option C: Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/github)

Connect the **deadpanther/builddy** GitHub repository in Railway. The repo root [`railway.toml`](railway.toml) configures the backend Dockerfile and health check. Set `GLM_API_KEY` (and optional cloud tokens) in the service variables.

To publish a reusable template URL later, create a template in the [Railway dashboard](https://railway.app) and replace this link.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GLM_API_KEY` | Yes | - | API key from open.bigmodel.cn |
| `GLM_BASE_URL` | No | `https://open.bigmodel.cn/api/paas/v4/` | GLM API base URL |
| `GLM_MODEL` | No | `glm-5.1` | Primary model for planning/review |
| `GLM_FAST_MODEL` | No | `glm-4.5` | Fast model for bulk generation |
| `GLM_VISION_MODEL` | No | `glm-5v-turbo` | Vision model for screenshot review |
| `ENABLE_AUTOPILOT` | No | `true` | Auto-fix runtime errors |
| `ENABLE_AUTO_TEST_GEN` | No | `true` | Generate test suites |
| `ENABLE_THINKING` | No | `true` | Enable chain-of-thought |
| `ENABLE_WEB_SEARCH` | No | `true` | Enable web search augmentation |
| `ENABLE_IMAGE_GEN` | No | `true` | Enable CogView image generation |
| `TWITTER_BEARER_TOKEN` | No | - | Twitter API v2 bearer token |
| `RAILWAY_API_TOKEN` | No | - | Railway deploy token |
| `GITHUB_TOKEN` | No | - | GitHub token for cloud deploy |
| `DATABASE_URL` | No | `sqlite:///./buildy.db` | Database connection string |

---

## API Endpoints

### Builds

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/builds` | Create build from text prompt |
| `POST` | `/api/builds/from-image` | Create build from screenshot |
| `GET` | `/api/builds` | List builds (filter by status, paginate) |
| `GET` | `/api/builds/{id}` | Get build details |
| `GET` | `/api/builds/{id}/steps` | Get pipeline step log |
| `GET` | `/api/builds/{id}/stream` | SSE real-time progress |
| `POST` | `/api/builds/{id}/modify` | Modify existing build |
| `POST` | `/api/builds/{id}/remix` | Remix as new build |
| `POST` | `/api/builds/{id}/deploy` | Manually trigger deploy |
| `POST` | `/api/builds/{id}/cloud-deploy` | Deploy to Railway/Render |
| `GET` | `/api/builds/{id}/deploy-status` | Check cloud deploy status |
| `GET` | `/api/builds/{id}/download` | Download as ZIP |
| `GET` | `/api/builds/{id}/files` | Get build files |
| `PUT` | `/api/builds/{id}/files` | Update a build file |
| `GET` | `/api/builds/{id}/chain` | Get build history chain |
| `POST` | `/api/builds/{id}/retry` | Retry a failed build |
| `DELETE` | `/api/builds/{id}` | Delete a build |
| `POST` | `/api/builds/{id}/generate-tests` | Generate test suite |

### Prompts & Experiments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/prompts/versions` | List prompt versions |
| `POST` | `/api/prompts/versions` | Create prompt version |
| `GET` | `/api/prompts/versions/{id}` | Get prompt version |
| `PATCH` | `/api/prompts/versions/{id}` | Update prompt version |
| `DELETE` | `/api/prompts/versions/{id}` | Delete prompt version |
| `GET` | `/api/prompts/experiments` | List A/B experiments |
| `POST` | `/api/prompts/experiments` | Create experiment |
| `GET` | `/api/prompts/experiments/{id}` | Get experiment |
| `PATCH` | `/api/prompts/experiments/{id}` | Update experiment |
| `POST` | `/api/prompts/experiments/{id}/record-result` | Record experiment result |
| `POST` | `/api/prompts/assign` | Assign variant to user |
| `POST` | `/api/prompts/assignments` | Get assignments |

### Gallery & Social

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/gallery` | Browse deployed apps |
| `GET` | `/api/gallery/{id}` | Get gallery app |
| `GET` | `/api/twitter/status` | Twitter bot status |
| `POST` | `/api/twitter/poll` | Poll for mentions |
| `POST` | `/api/twitter/ingest` | Ingest a tweet |
| `GET` | `/api/twitter/mentions` | List recent mentions |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/processes` | List running processes |

Full interactive docs at `http://localhost:8000/docs` (Swagger UI).

---

## Build Pipeline

```
pending -> planning -> coding -> reviewing -> polishing -> validating -> autopilot -> testing -> deploying -> deployed
                                                                                                                   |
                                                                                                              -> failed
```

1. **Parse** -- Extract app name, features, tech stack from prompt
2. **Plan** -- Design layout, component hierarchy, data flow
3. **Code** -- Generate complete HTML/CSS/JS (or fullstack Node.js)
4. **Review** -- Self-review for bugs, accessibility, responsiveness
5. **Polish** -- Add animations, dark mode, empty states, micro-interactions
6. **Visual Validate** -- Screenshot in headless browser, GLM-5V fixes visual issues
7. **Autopilot** -- Run in headless browser, detect JS errors, auto-fix iteratively (up to 3 rounds)
8. **Test Gen** -- Generate test suite (HTML tests or Node.js API tests)
9. **Deploy** -- Serve static files or push to cloud (Railway/Render)

---

## Project Structure

```
builddy/
+-- backend/                  # FastAPI backend
|   +-- agent/
|   |   +-- llm.py           # GLM API client (async httpx)
|   |   +-- pipeline.py      # Build + modify + fullstack pipelines
|   |   +-- prompts.py       # System prompts per pipeline stage
|   |   +-- autopilot.py     # Headless browser error recovery loop
|   |   +-- test_gen.py      # Auto test suite generation
|   +-- routers/
|   |   +-- builds.py        # Build CRUD, modify, remix, deploy, cloud
|   |   +-- gallery.py       # Deployed apps gallery
|   |   +-- prompts.py       # A/B testing, prompt versions
|   |   +-- twitter.py       # Twitter/X bot integration
|   +-- services/
|   |   +-- deployer.py      # Static HTML deployment
|   |   +-- cloud_deploy.py  # Railway/Render cloud deployment
|   |   +-- visual_validator.py  # Headless browser validation
|   |   +-- twitter_scraper.py   # Twitter API v2 client
|   |   +-- process_manager.py   # Background process management
|   +-- models.py            # SQLModel schemas
|   +-- database.py          # SQLite setup
|   +-- config.py            # Pydantic settings (.env)
|   +-- tests/               # 449 tests, 80% coverage
|   +-- Dockerfile
|   +-- pyproject.toml
|
+-- frontend/                 # Next.js 14 App Router
|   +-- src/
|       +-- app/             # Pages: dashboard, build detail, gallery, autopsy
|       +-- components/      # AgentSteps, BuildFeed, AppPreview, etc.
|       +-- lib/             # API client, TypeScript types
|
+-- autopsy-backend/          # Code Autopsy API (FastAPI, port 8001)
|   +-- agent/               # Forensic analysis agent
|
+-- docs/                     # Documentation
+-- docker-compose.yml
+-- README.md
```

---

## Testing

```bash
cd backend

# Run all tests
uv run pytest tests/ -q

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=term-missing
```

**449 tests | 80% coverage | ~80s runtime**

---

## Deployment

### Railway

1. Fork the repo
2. Create a new Railway project from the GitHub repo
3. Set `GLM_API_KEY` in Railway environment variables
4. Deploy the backend service (auto-detected from Dockerfile)
5. Deploy the frontend with `NEXT_PUBLIC_API_URL` pointing to your backend

### Render

1. Create a new Web Service from the GitHub repo
2. Set root directory to `backend`
3. Build command: `pip install uv && uv sync`
4. Start command: `uv run uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add `GLM_API_KEY` environment variable

---

## License

MIT
