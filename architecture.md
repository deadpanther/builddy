# Buildy (@builddy) — Architecture Plan

## System Overview
Buildy is a Twitter-integrated AI agent. When someone mentions @builddy with an app request, GLM 5.1 autonomously generates a complete web app and deploys it. The user gets a live URL back in a tweet reply.

---

## Backend API Endpoints (FastAPI)

### Build Endpoints
- `POST /api/builds` -- Trigger a new build from a tweet (internal + manual)
- `GET /api/builds` -- List all builds with status
- `GET /api/builds/{build_id}` -- Get build details + generated code + URL
- `GET /api/builds/{build_id}/steps` -- Get agent steps for a build
- `POST /api/builds/{build_id}/deploy` -- Manually trigger deploy

### Twitter Endpoints
- `GET /api/twitter/status` -- Twitter polling status
- `POST /api/twitter/poll` -- Manually trigger mention check
- `GET /api/twitter/mentions` -- Recent mentions

### Gallery Endpoints
- `GET /api/gallery` -- Public gallery of all deployed apps
- `GET /api/gallery/{build_id}` -- Single app details

### Health
- `GET /api/health` -- Health check

---

## Database Schema (SQLite + SQLModel)

### builds
```
id: TEXT PRIMARY KEY (UUID)
tweet_id: TEXT -- Twitter tweet ID that triggered the build
tweet_text: TEXT -- Full tweet text
twitter_username: TEXT -- Who requested it
app_name: TEXT -- Generated app name
app_description: TEXT -- What the app does
prompt: TEXT -- Parsed prompt from tweet
status: TEXT -- pending, planning, coding, reviewing, deploying, deployed, failed
generated_code: TEXT -- Complete HTML/CSS/JS code
deploy_url: TEXT -- URL where app is deployed
steps: TEXT -- JSON array of agent reasoning steps
error: TEXT -- Error message if failed
created_at: DATETIME
updated_at: DATETIME
deployed_at: DATETIME
```

### mentions
```
id: TEXT PRIMARY KEY
tweet_id: TEXT UNIQUE -- Twitter tweet ID
tweet_text: TEXT
twitter_username: TEXT
processed: BOOLEAN -- Whether we've handled this mention
build_id: TEXT FOREIGN KEY -> builds.id (nullable)
created_at: DATETIME
```

---

## GLM 5.1 Agent Pipeline

### Step 1: Parse Request
- Extract the app request from the tweet text
- Remove "@builddy" mention and any boilerplate
- Identify the type of app (tool, game, tracker, generator, etc.)

### Step 2: Plan Architecture
- GLM 5.1 generates a plan for the app structure
- Decides: single HTML file vs multi-component
- Plans: layout, features, styling approach, interactivity
- Uses tool calling to define the plan structure

### Step 3: Generate Code
- GLM 5.1 generates complete HTML/CSS/JS in a single file
- Uses its 200K context to maintain coherence across a full app
- Includes: responsive design, clean UI, working functionality
- No external dependencies (pure HTML/CSS/JS for maximum portability)

### Step 4: Self-Review
- GLM 5.1 reviews its own code for bugs
- Checks: JS syntax, CSS completeness, feature completeness
- Fixes any issues found

### Step 5: Deploy
- Save the HTML file to a static hosting directory
- Generate a unique subdomain/path URL
- Alternative: deploy to Netlify/Vercel via API

### Step 6: Reply
- Post a reply tweet with the deployed URL
- Include a screenshot if possible

---

## Twitter Integration Flow

### Polling Approach (simpler, no webhook needed)
1. Every 30 seconds, poll `GET /2/tweets/search/recent?query=@builddy`
2. Filter out already-processed mentions (check DB)
3. For each new mention:
   a. Save to `mentions` table
   b. Extract the app request
   c. Create a build entry
   d. Run the GLM 5.1 agent pipeline
   e. Reply with the deployed URL

### X API v2 Endpoints Used
- `GET /2/tweets/search/recent` -- Search for @builddy mentions
- `POST /2/tweets` -- Post reply tweets
- Uses Bearer Token auth

---

## Deployment Engine

### Option A: Static File Hosting (Primary)
- Save HTML files to a `deployed/` directory
- Serve via FastAPI static files at `/apps/{build_id}/`
- Simple, reliable, no external service needed

### Option B: Netlify Deploy (Enhanced)
- Use Netlify API to deploy each app as a separate site
- Gives each app its own subdomain
- More impressive for demo but adds complexity

### For the hackathon: Option A is primary, Option B if time permits

---

## Frontend Pages (Next.js)

### Dashboard Page (/)
- Live feed of recent builds
- Each build card shows: tweet text, app name, status, deploy URL
- Real-time status updates (polling or SSE)
- "Try it" button to submit a test build

### Build Detail Page (/build/[id])
- Full agent thinking visualization
- Step-by-step breakdown of what GLM 5.1 did
- Live preview of the generated app (iframe)
- Raw code view
- Original tweet embed

### Gallery Page (/gallery)
- Grid of all deployed apps
- Click to open any app
- Search/filter by type

### Components
- `<BuildCard>` -- Summary card for a build
- `<BuildFeed>` -- Live feed of builds
- `<AgentSteps>` -- Step-by-step agent reasoning visualization
- `<CodePreview>` -- Syntax-highlighted code view
- `<AppPreview>` -- iframe preview of deployed app
- `<TweetEmbed>` -- Show original tweet
- `<StatusBadge>` -- Build status indicator
- `<SubmitBuild>` -- Manual build submission form

---

## Implementation Checklist

### Backend
- [ ] FastAPI app setup with CORS
- [ ] SQLite database with SQLModel models
- [ ] Build CRUD endpoints
- [ ] GLM 5.1 API client (OpenAI-compatible, base_url=https://open.z.ai/api/paas/v4/)
- [ ] Agent pipeline: parse -> plan -> code -> review -> deploy
- [ ] Tool definitions for GLM 5.1 function calling
- [ ] Twitter API v2 polling service
- [ ] Twitter reply service
- [ ] Static file deployment engine
- [ ] Mention deduplication
- [ ] Health check endpoint

### Frontend
- [ ] Next.js 14 project with App Router
- [ ] Tailwind + shadcn/ui setup
- [ ] Dashboard page with live build feed
- [ ] Build detail page with agent steps
- [ ] Gallery page
- [ ] Code preview component
- [ ] App preview (iframe) component
- [ ] Manual build submission form
- [ ] Auto-refresh / polling for status updates

### Integration
- [ ] End-to-end: tweet mention -> build -> deploy -> reply
- [ ] Dashboard shows builds in real-time
- [ ] Agent thinking visible in UI
- [ ] Demo script: submit a test build and watch it complete

---

## File Structure
```
project/
  backend/
    main.py              -- FastAPI app entry point
    models.py            -- SQLModel database models
    config.py            -- Settings (API keys, env vars)
    database.py          -- DB connection and setup
    requirements.txt
    .env                 -- API keys (GLM, Twitter)
    agent/
      __init__.py
      llm.py             -- GLM 5.1 API client
      pipeline.py        -- Main agent pipeline (parse->plan->code->review->deploy)
      prompts.py         -- System prompts for each stage
    routers/
      builds.py          -- Build CRUD endpoints
      twitter.py         -- Twitter status + manual poll
      gallery.py         -- Gallery endpoints
    services/
      twitter.py         -- Twitter API v2 polling + replies
      deployer.py        -- Static file deployment
    deployed/            -- Directory for deployed app HTML files
  frontend/
    (Next.js 14 project)
    src/
      app/
        page.tsx         -- Dashboard
        layout.tsx
        build/[id]/page.tsx -- Build detail
        gallery/page.tsx -- Gallery
      components/
        BuildCard.tsx
        BuildFeed.tsx
        AgentSteps.tsx
        CodePreview.tsx
        AppPreview.tsx
        SubmitBuild.tsx
        StatusBadge.tsx
      lib/
        api.ts           -- API client
        types.ts         -- TypeScript types
    package.json
```
