# API Reference

Base URL: `http://localhost:8000`

Interactive docs available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Builds

### Create Build

```bash
curl -X POST http://localhost:8000/api/builds \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a pomodoro timer with dark mode"}'
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Natural language app description |
| `complexity` | string | No | `simple` or `fullstack` (default: auto-detect) |

**Response:** `BuildResponse`

```json
{
  "id": "abc123",
  "status": "pending",
  "app_name": "Pomodoro Timer",
  "build_type": "text",
  "created_at": "2026-04-09T12:00:00Z"
}
```

### Create Build from Screenshot

```bash
curl -X POST http://localhost:8000/api/builds/from-image \
  -H "Content-Type: multipart/form-data" \
  -F "image=@screenshot.png" \
  -F "prompt=Add a settings panel"
```

### List Builds

```bash
curl "http://localhost:8000/api/builds?status=deployed&offset=0&limit=20"
```

**Query Params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | string | all | Filter by status |
| `offset` | int | 0 | Pagination offset |
| `limit` | int | 50 | Page size |

### Get Build

```bash
curl http://localhost:8000/api/builds/{build_id}
```

### Get Build Steps

```bash
curl http://localhost:8000/api/builds/{build_id}/steps
```

Returns the pipeline step log with timestamps and status.

### Stream Build Progress (SSE)

```bash
curl -N http://localhost:8000/api/builds/{build_id}/stream
```

Server-Sent Events stream. Event types: `connected`, `status`, `step`, `ping`, `done`.

### Modify Build

```bash
curl -X POST http://localhost:8000/api/builds/{build_id}/modify \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Add sound effects"}'
```

### Remix Build

```bash
curl -X POST http://localhost:8000/api/builds/{build_id}/remix \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Make it a kanban board instead"}'
```

### Deploy Build

```bash
curl -X POST http://localhost:8000/api/builds/{build_id}/deploy
```

### Cloud Deploy

```bash
curl -X POST http://localhost:8000/api/builds/{build_id}/cloud-deploy \
  -H "Content-Type: application/json" \
  -d '{"provider": "railway"}'
```

**Provider options:** `railway`, `render`

### Get Deploy Status

```bash
curl http://localhost:8000/api/builds/{build_id}/deploy-status
```

### Download Build (ZIP)

```bash
curl -O http://localhost:8000/api/builds/{build_id}/download
```

### Get Build Files

```bash
curl http://localhost:8000/api/builds/{build_id}/files
```

### Update Build File

```bash
curl -X PUT http://localhost:8000/api/builds/{build_id}/files \
  -H "Content-Type: application/json" \
  -d '{"file_path": "index.html", "content": "<h1>Updated</h1>"}'
```

### Get Build Chain

```bash
curl http://localhost:8000/api/builds/{build_id}/chain
```

Returns the full parent-child chain of builds (original -> modifications -> remixes).

### Retry Build

```bash
curl -X POST http://localhost:8000/api/builds/{build_id}/retry
```

### Delete Build

```bash
curl -X DELETE http://localhost:8000/api/builds/{build_id}
```

### Generate Tests

```bash
curl -X POST http://localhost:8000/api/builds/{build_id}/generate-tests
```

---

## Prompts & Experiments

### List Prompt Versions

```bash
curl http://localhost:8000/api/prompts/versions
```

### Create Prompt Version

```bash
curl -X POST http://localhost:8000/api/prompts/versions \
  -H "Content-Type: application/json" \
  -d '{"name": "v2-planner", "system_prompt": "You are an app architect...", "stage": "plan"}'
```

### Get / Update / Delete Prompt Version

```bash
curl http://localhost:8000/api/prompts/versions/{version_id}
curl -X PATCH http://localhost:8000/api/prompts/versions/{version_id} -d '{"is_active": false}'
curl -X DELETE http://localhost:8000/api/prompts/versions/{version_id}
```

### List Experiments

```bash
curl http://localhost:8000/api/prompts/experiments
```

### Create Experiment

```bash
curl -X POST http://localhost:8000/api/prompts/experiments \
  -d '{"name": "plan-ab-test", "control_version_id": "v1", "variant_version_id": "v2", "traffic_split": 0.5}'
```

### Record Experiment Result

```bash
curl -X POST http://localhost:8000/api/prompts/experiments/{id}/record-result \
  -d '{"variant": "control", "success": true, "build_id": "abc123"}'
```

### Assign Variant

```bash
curl -X POST http://localhost:8000/api/prompts/assign \
  -d '{"experiment_id": "exp1", "user_id": "user123"}'
```

---

## Gallery

```bash
curl http://localhost:8000/api/gallery
curl http://localhost:8000/api/gallery/{build_id}
```

---

## Twitter

```bash
curl http://localhost:8000/api/twitter/status
curl -X POST http://localhost:8000/api/twitter/poll
curl -X POST http://localhost:8000/api/twitter/ingest -d '{"tweet_id": "123", "text": "@builddy build a calculator"}'
curl http://localhost:8000/api/twitter/mentions
```

Requires Twitter API v2 credentials in environment.

---

## System

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/processes
```
