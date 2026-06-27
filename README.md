# AI Digest

AI Digest is a full-stack news aggregation and summarization application that automatically fetches AI/ML articles from curated RSS feeds and the HackerNews API, generates concise AI-powered summaries using a local Ollama LLM, and delivers personalized daily or weekly email digests to subscribers — all while exposing the article feed through a clean Next.js frontend.

---

## Features

- **Automated news fetching** — polls RSS feeds and HackerNews every 2 hours via APScheduler
- **Local AI summarization** — uses Ollama (default: `llama3.2`) to summarize articles on-device; no external AI API required
- **Email digests** — daily (08:00 UTC) and weekly (Monday 08:00 UTC) digests sent via Resend
- **Email confirmation flow** — double-opt-in subscription with token-based confirmation and one-click unsubscribe
- **Paginated article feed** — Next.js 14 App Router frontend with server components and Tailwind CSS
- **Article detail pages** — full article content with AI summary
- **Admin endpoints** — manually trigger fetch and summarize jobs via REST
- **Docker Compose** — single command spins up API, frontend, and Ollama
- **Database migrations** — Alembic-managed SQLAlchemy 2.0 schema with automatic seeding of default sources

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required for the FastAPI backend |
| [uv](https://docs.astral.sh/uv/) | Latest | Python package/project manager |
| Node.js | 18+ | Required for the Next.js frontend |
| [Ollama](https://ollama.com/) | Latest | Local LLM runtime for summarization |
| Resend API key | — | Optional — needed only to send email digests |

---

## Quick Start (Local Dev)

### 1. Clone and configure environment variables

```bash
git clone <repo-url>
cd ai_digest
cp .env.example .env
# Edit .env with your values (see Configuration section below)
```

### 2. Pull the Ollama model

```bash
ollama pull llama3.2
```

### 3. Start the FastAPI backend

```bash
cd apps/api
cp .env.example .env   # if you haven't already set up the root .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Default news sources are seeded automatically on first startup.

### 4. Start the Next.js frontend

Open a second terminal:

```bash
cd apps/web
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### 5. Trigger an initial news fetch (optional)

```bash
curl -X POST http://localhost:8000/admin/fetch
curl -X POST http://localhost:8000/admin/summarize
```

---

## Docker Quick Start

Ensure Docker and Docker Compose are installed, then:

```bash
cp .env.example .env
# Edit .env with your values

docker compose up --build
```

This starts three services:

| Service | Port | Description |
|---|---|---|
| `api` | 8000 | FastAPI backend |
| `web` | 3000 | Next.js frontend |
| `ollama` | 11434 | Local LLM runtime |

Pull the Ollama model into the running container:

```bash
docker compose exec ollama ollama pull llama3.2
```

To stop:

```bash
docker compose down
```

---

## API Reference

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Health check — returns `{"status": "ok"}` |
| `GET` | `/sources` | List all configured news sources |
| `GET` | `/articles` | Paginated article list (`?page=1&limit=20&source_id=`) |
| `GET` | `/articles/{id}` | Single article with AI summary |
| `POST` | `/subscribe` | Subscribe to digest (`{email, cadence: "daily"\|"weekly"}`) |
| `GET` | `/confirm/{token}` | Confirm subscription — redirects to frontend |
| `GET` | `/unsubscribe/{token}` | Unsubscribe — removes subscription |
| `POST` | `/admin/fetch` | Manually trigger news fetch across all sources |
| `POST` | `/admin/summarize` | Summarize up to 20 pending articles |
| `POST` | `/admin/digest/daily` | Trigger the daily email digest immediately |
| `POST` | `/admin/digest/weekly` | Trigger the weekly email digest immediately |

---

## Configuration

All configuration is provided through environment variables. Copy `.env.example` to `.env` and fill in the values.

| Variable | Default | Required | Description |
|---|---|---|---|
| `DATABASE_URL` | `sqlite:///./digest.db` | No | SQLAlchemy database URL. Use SQLite for dev or a Postgres URL for production. |
| `OLLAMA_URL` | `http://localhost:11434` | No | Base URL of the running Ollama instance. Set to `http://ollama:11434` when using Docker Compose. |
| `OLLAMA_MODEL` | `llama3.2` | No | Ollama model name used for summarization. Any model available in your Ollama instance is valid. |
| `RESEND_API_KEY` | — | Yes (for email) | API key from [resend.com](https://resend.com). Email sending is skipped if not set. |
| `RESEND_FROM` | — | Yes (for email) | Sender address shown on digest emails, e.g. `digest@yourdomain.com`. |
| `SITE_URL` | `http://localhost:3000` | No | Public URL of the frontend. Used to build confirmation and unsubscribe links in emails. |
| `CORS_ORIGINS` | `http://localhost:3000` | No | Comma-separated list of allowed CORS origins for the API. |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | No | Public API base URL consumed by the Next.js frontend. |
| `SUMMARIZER_ENABLED` | `true` | No | Set to `false` to disable Ollama summarization (used in cloud deployments without GPU). |
| `ADMIN_SECRET` | — | Yes | Secret value required in the `X-Admin-Key` header to access `/admin/*` endpoints. |

---

## Architecture Overview

The system is built around a sequential pipeline that runs automatically on a schedule:

```
RSS / HackerNews
       │
       ▼
  [Fetcher]  ── every 2 hours ──▶  Articles stored in DB (unsummarized)
       │
       ▼
 [Summarizer] ── every 30 min ──▶  Ollama generates summary per article
       │
       ▼
  [Frontend]  ◀── Next.js reads /articles endpoint ── display to users
       │
       ▼
  [Digest Builder] ── daily 08:00 UTC / weekly Mon 08:00 UTC
       │              builds HTML email from recent summaries
       ▼
  [Resend API] ──▶  Email delivered to confirmed subscribers
```

- **Fetcher** (`apps/api/app/fetcher.py`) — uses `feedparser` for RSS sources and `httpx` for the HackerNews Algolia API. Deduplicates by URL.
- **Summarizer** (`apps/api/app/summarizer.py`) — sends article content to the Ollama `/api/generate` endpoint and stores the result.
- **Scheduler** (`apps/api/app/scheduler.py`) — APScheduler `BackgroundScheduler` wired up in the FastAPI lifespan.
- **Digest** (`apps/api/app/digest.py`) — builds an HTML email from summarized articles and dispatches it via the Resend Python SDK.
- **Frontend** (`apps/web/`) — Next.js 14 App Router with server-side data fetching, `ArticleCard` / `NavBar` components, and a `SubscribeForm`.

---

## Adding News Sources

### Option A — Edit `DEFAULT_SOURCES` in `db.py`

Open `apps/api/app/db.py` and add an entry to the `DEFAULT_SOURCES` list:

```python
DEFAULT_SOURCES = [
    # ... existing sources ...
    {
        "name": "My New Feed",
        "url": "https://example.com/feed.xml",
        "source_type": "rss",        # "rss" or "hackernews"
    },
]
```

On next startup (or after running `init_db()`), the new source will be seeded automatically if it does not already exist.

### Option B — Insert directly into the database

```bash
# SQLite example
sqlite3 apps/api/digest.db \
  "INSERT INTO sources (name, url, source_type, active) VALUES ('My New Feed', 'https://example.com/feed.xml', 'rss', 1);"
```

After adding a source, trigger an immediate fetch:

```bash
curl -X POST http://localhost:8000/admin/fetch
```

---

## Cloud Deployment

The app deploys to **Vercel** (frontend) + **Render** (backend) + **Neon** (PostgreSQL). Scheduled jobs run via **GitHub Actions** to avoid Render's free-tier sleep issue.

### 1. Create a Neon database
Go to [neon.tech](https://neon.tech) → New Project → copy the connection string (`postgresql://...`).

### 2. Deploy backend on Render
Connect your GitHub repo at [render.com](https://render.com) → New → Blueprint. Render reads `render.yaml` and creates the web service. Then in the Render dashboard set:
- `DATABASE_URL` = Neon connection string
- `SITE_URL` = your Vercel URL (after step 3)
- `CORS_ORIGINS` = your Vercel URL
- `RESEND_API_KEY`, `RESEND_FROM` = your Resend credentials

### 3. Deploy frontend on Vercel
Import the repo at [vercel.com](https://vercel.com). Vercel auto-detects `vercel.json`. Set env var:
- `NEXT_PUBLIC_API_URL` = your Render service URL

### 4. Add GitHub Actions secrets
In repo → Settings → Secrets → Actions:
- `API_URL` = Render service URL
- `ADMIN_SECRET` = value from Render dashboard

GitHub Actions then handles scheduled fetches (every 2h) and digest sends (daily/weekly) even when Render sleeps.

> **Note:** Set `SUMMARIZER_ENABLED=false` on Render — Ollama cannot run on free cloud tiers. Articles show excerpts instead of AI summaries in the cloud deployment.

---

## Project Structure

```
ai_digest/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py         # FastAPI application and route definitions
│   │   │   ├── models.py       # SQLAlchemy models (Source, Article, Subscriber, DigestLog)
│   │   │   ├── schemas.py      # Pydantic v2 request/response schemas
│   │   │   ├── db.py           # Database engine, session factory, and source seeding
│   │   │   ├── fetcher.py      # RSS (feedparser) and HackerNews article fetcher
│   │   │   ├── summarizer.py   # Ollama LLM client
│   │   │   ├── digest.py       # HTML email builder and Resend dispatcher
│   │   │   └── scheduler.py    # APScheduler job definitions
│   │   ├── alembic/            # Database migration scripts
│   │   ├── pyproject.toml      # uv project manifest
│   │   └── .env.example
│   └── web/                    # Next.js 14 App Router frontend
│       ├── app/
│       │   ├── page.tsx              # Paginated article feed
│       │   ├── article/[id]/page.tsx # Article detail with summary
│       │   └── subscribe/page.tsx    # Subscription form
│       ├── components/               # NavBar, ArticleCard, SubscribeForm
│       ├── lib/api.ts                # Typed fetch helpers
│       └── package.json
├── docker-compose.yml          # Compose file for api + web + ollama
├── render.yaml                 # Render.com deployment config
├── vercel.json                 # Vercel deployment config
├── .github/
│   └── workflows/
│       ├── scheduled_fetch.yml   # Fetch news every 2h via GitHub Actions
│       └── scheduled_digest.yml  # Send digests daily/weekly via GitHub Actions
└── .env.example
```
