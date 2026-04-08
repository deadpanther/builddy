# Contributing to Builddy

Thanks for your interest in contributing! Builddy is an AI-powered app builder that turns natural language descriptions into deployed web apps.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Setup

```bash
# Clone the repo
git clone https://github.com/deadpanther/builddy.git
cd builddy

# Backend
cd backend
cp .env.example .env  # Fill in your GLM API key
uv sync
uv run uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
cp .env.local.example .env.local  # Fill in Auth0 config
npm install --legacy-peer-deps
npm run dev

# Autopsy backend (new terminal)
cd autopsy-backend
cp .env.example .env
uv sync
uv run uvicorn main:app --reload --port 8001
```

### Running Tests

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm test
```

## Development Workflow

1. Create a branch from `main`: `git checkout -b feat/your-feature`
2. Make your changes
3. Run linting: `cd backend && uv run ruff check .`
4. Run tests: `cd backend && uv run pytest`
5. Commit with conventional format: `feat: add cool feature`
6. Open a PR against `main`

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` new feature
- `fix:` bug fix
- `refactor:` code restructuring
- `docs:` documentation
- `test:` adding tests
- `chore:` maintenance

## Architecture Overview

```
builddy/
  backend/           # FastAPI - main API + AI pipeline
    agent/           # GLM-powered multi-agent pipeline
      pipeline.py    # Orchestration (parse -> plan -> code -> review -> deploy)
      llm.py         # GLM API client with fallback chain
      prompts.py     # All agent system prompts
      components.py  # Tailwind component library
    routers/         # API endpoints (builds, twitter, gallery)
    services/        # Deployer, event bus, process manager
  frontend/          # Next.js 14 App Router
    src/app/         # Pages (dashboard, build detail, gallery, autopsy)
    src/components/  # Shared UI components
  autopsy-backend/   # Code Autopsy service (repo analysis)
```

## Code Style

- **Python**: Ruff for linting, 120 char line length
- **TypeScript**: ESLint + Next.js config
- **Immutability**: Prefer creating new objects over mutation
- **Files**: Keep under 400 lines; extract when they grow

## Reporting Issues

Use [GitHub Issues](https://github.com/deadpanther/builddy/issues) with the templates provided.
