# Deployment Guide

## Local Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 18+
- GLM API key from [open.bigmodel.cn](https://open.bigmodel.cn)

### Setup

```bash
git clone https://github.com/deadpanther/builddy.git
cd builddy

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your GLM_API_KEY
```

### Start Backend

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

### Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### Start Code Autopsy (optional)

```bash
cd autopsy-backend
cp ../backend/.env .env
uv sync
uv run uvicorn main:app --reload --port 8001
```

### Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Code Autopsy | http://localhost:8001 |
| Deployed Apps | http://localhost:8000/apps/{id}/ |

---

## Docker Deployment

### Quick Start

```bash
# Create .env with your keys
echo "GLM_API_KEY=your_key_here" > .env

# Build and start all services
docker compose up --build -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Docker Compose Configuration

The `docker-compose.yml` defines two services:

- **backend**: FastAPI on port 8000 with health checks
- **frontend**: Next.js on port 3000, waits for backend health check

Volumes persist the SQLite database and deployed app files.

### Custom Configuration

```yaml
# Add to docker-compose.yml under backend.environment:
environment:
  - ENABLE_AUTOPILOT=true
  - ENABLE_AUTO_TEST_GEN=true
  - GLM_MODEL=glm-5.1
```

---

## Railway Deployment

### Option 1: Deploy from GitHub

Use the README **Deploy on Railway** button (opens [railway.app/new/github](https://railway.app/new/github)), connect GitHub, and select **deadpanther/builddy**. The repository root [`railway.toml`](../railway.toml) points Railway at `backend/Dockerfile` and `/api/health`. Set `GLM_API_KEY` in the service variables.

You can later publish a reusable template in the Railway dashboard and link it from the README if you want a fixed template URL.

### Option 2: Manual Setup

1. Create a new project at [railway.app](https://railway.app)
2. Connect your GitHub repo
3. Add the **backend** service:
   - Root directory: `backend`
   - Environment variables:
     - `GLM_API_KEY` (required)
     - `GLM_BASE_URL` (optional)
     - `ENABLE_AUTOPILOT=true`
     - `ENABLE_AUTO_TEST_GEN=true`
4. Add the **frontend** service:
   - Root directory: `frontend`
   - Build arg: `NEXT_PUBLIC_API_URL=https://your-backend.railway.app`
5. Railway auto-generates a domain for each service

### Environment Variables for Railway

```env
GLM_API_KEY=your_key
GLM_MODEL=glm-5.1
GLM_FAST_MODEL=glm-4.5
DATABASE_URL=sqlite:///./buildy.db
ENABLE_AUTOPILOT=true
ENABLE_AUTO_TEST_GEN=true
RAILWAY_API_TOKEN=your_railway_token  # for cloud deploy feature
```

---

## Render Deployment

1. Create a new **Web Service** at [render.com](https://render.com)
2. Connect your GitHub repo
3. Configure:
   - **Root directory**: `backend`
   - **Build command**: `pip install uv && uv sync`
   - **Start command**: `uv run uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `GLM_API_KEY` (required)
   - `PORT` (auto-set by Render)

---

## Production Considerations

### Reverse Proxy

Use Nginx or Caddy as a reverse proxy:

```nginx
server {
    listen 80;
    server_name builddy.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /apps/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### SSL

Use Let's Encrypt with certbot or Cloudflare for automatic SSL.

### Database

For production, consider upgrading from SQLite to PostgreSQL:

```env
DATABASE_URL=postgresql://user:pass@host:5432/builddy
```

### Scaling

- The backend is stateless (except SQLite) -- run multiple workers:
  ```bash
  uv run uvicorn main:app --workers 4 --port 8000
  ```
- Use Redis for SSE pub/sub when running multiple workers
- Static app files should be stored in S3/Cloudflare R2 for multi-instance access

### Monitoring

- Health check: `GET /api/health`
- Process monitoring: `GET /api/processes`
- Add Sentry/DataDog for error tracking
