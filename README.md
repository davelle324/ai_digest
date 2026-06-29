# AI Digest

AI Digest is a full-stack news aggregation app that automatically fetches AI/ML articles from 15 curated sources, displays them with category and source filtering, and delivers personalized daily or weekly email digests to subscribers.

---

## Features

- **15 curated sources** across 5 categories — Top Stories, Research, Open Source, Company Releases, Community Buzz
- **Automated fetching** — every 2 hours via GitHub Actions + APScheduler
- **Category and source filtering** — browse by category or drill into a specific source
- **Local AI summarization** — uses Ollama (default: `llama3.2`) on-device; no external AI API required
- **Email digests** — daily (08:00 UTC) and weekly (Monday 08:00 UTC) via Resend
- **Double opt-in subscriptions** — token-based email confirmation and one-click unsubscribe
- **Docker Compose** — single command for local dev with API, frontend, and Ollama

---

## Quick Start (Local)

```bash
git clone <repo-url>
cd ai_digest
cp .env.example .env
# Edit .env — set ADMIN_SECRET to anything (e.g. "localdev"), fill in RESEND_* if you want emails

./run-local.sh
```

That's it. The script checks prerequisites, starts the FastAPI backend on `:8000` and Next.js on `:3000`, and runs database migrations automatically.

To trigger your first news fetch:
```bash
curl -X POST http://localhost:8000/admin/fetch \
  -H "X-Admin-Key: localdev"
```

---

## Prerequisites

| Tool | Notes |
|---|---|
| Python 3.11+ | For the FastAPI backend |
| [uv](https://docs.astral.sh/uv/) | Python package manager |
| Node.js 18+ | For the Next.js frontend |
| [Ollama](https://ollama.com/) | Optional — local LLM for article summarization |

---

## Configuration

Copy `.env.example` to `.env` and fill in values. The root `.env` is the single source of truth for both the API and frontend when running locally.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/digest.db` | SQLite for local; Neon/Postgres URL for cloud |
| `ADMIN_SECRET` | — | Required. Any string you choose. Used to protect `/admin/*` endpoints |
| `RESEND_API_KEY` | — | From [resend.com](https://resend.com). Email sending skipped if not set |
| `RESEND_FROM` | — | Verified sender address for digest emails |
| `SITE_URL` | `http://localhost:3000` | Frontend URL — used in confirmation/unsubscribe email links |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins for the API |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API base URL for the frontend |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama instance URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model for summarization |
| `SUMMARIZER_ENABLED` | `true` | Set `false` to disable Ollama (used in cloud deploys) |

---

## Docker Quick Start

```bash
cp .env.example .env
docker compose up --build
# Pull the Ollama model into the container:
docker compose exec ollama ollama pull llama3.2
```

Services: API on `:8000`, frontend on `:3000`.

---

## API Reference

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/sources` | List enabled sources (sorted by category) |
| `GET` | `/sources/categories` | List category keys and display labels |
| `GET` | `/articles` | Paginated articles (`?page&limit&source_id&category`) |
| `GET` | `/articles/{id}` | Single article detail |
| `POST` | `/subscribe` | Subscribe (`{email, cadence: "daily"\|"weekly"}`, rate-limited) |
| `GET` | `/confirm/{token}` | Confirm subscription |
| `GET` | `/unsubscribe/{token}` | Unsubscribe |
| `POST` | `/admin/fetch` | Trigger background fetch (requires `X-Admin-Key`) |
| `POST` | `/admin/summarize` | Summarize up to 20 pending articles |
| `POST` | `/admin/digest/daily` | Trigger daily digest immediately |
| `POST` | `/admin/digest/weekly` | Trigger weekly digest immediately |

---

## News Sources

| Category | Sources |
|---|---|
| 🔥 Top Stories | OpenAI Blog, Anthropic, Google AI, TechCrunch AI, The Batch |
| 🧠 Research | arXiv cs.AI, arXiv cs.LG, arXiv cs.CL |
| 💻 Open Source | Hugging Face, Towards Data Science |
| 🏢 Company Releases | NVIDIA Blog, Meta AI |
| 👥 Community Buzz | HackerNews AI, Reddit r/MachineLearning, Reddit r/LocalLLaMA |

To add a source, add an entry to `DEFAULT_SOURCES` in `apps/api/app/db.py`. It will be seeded on next startup.

---

## Cloud Deployment

The app deploys to **Vercel** (frontend) + **Render** (backend). Scheduled jobs run via **GitHub Actions** to work around Render's free-tier sleep.

### 1. Deploy backend on Render

Render → **New → Web Service** → connect your repo → set Root Directory to `apps/api`.

Set these environment variables in the Render dashboard:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon/Postgres connection string (or leave SQLite for testing) |
| `ADMIN_SECRET` | A strong random string (`openssl rand -hex 32`) |
| `RESEND_API_KEY` | Your Resend API key |
| `RESEND_FROM` | Your verified sender address |
| `SITE_URL` | Your Vercel URL (set after step 2) |
| `CORS_ORIGINS` | Your Vercel URL (set after step 2) |
| `SUMMARIZER_ENABLED` | `false` |

### 2. Deploy frontend on Vercel

Vercel → **New Project** → import repo.

**Important:** In project Settings → General → **Root Directory**, set to `apps/web`.

Set this environment variable:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | Your Render service URL |

Trigger a redeploy after setting env vars (they're baked in at build time).

### 3. Update Render with Vercel URL

Go back to Render → Environment → update `SITE_URL` and `CORS_ORIGINS` to your Vercel URL.

### 4. Add GitHub Actions secrets

Repo → Settings → Secrets → Actions:

| Secret | Value |
|---|---|
| `API_URL` | Your Render service URL |
| `ADMIN_SECRET` | Same value as on Render |

GitHub Actions will then wake the API (health-check retry) and trigger fetches + digests on schedule even when Render sleeps.

---

## Project Structure

```
ai_digest/
├── apps/
│   ├── api/                    FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py         Routes and middleware
│   │   │   ├── models.py       SQLAlchemy models
│   │   │   ├── schemas.py      Pydantic v2 schemas
│   │   │   ├── db.py           DB setup, source seeding, category definitions
│   │   │   ├── fetcher.py      RSS + HackerNews fetcher (HTML-stripped excerpts)
│   │   │   ├── summarizer.py   Ollama client
│   │   │   ├── digest.py       Email builder and Resend dispatcher
│   │   │   └── scheduler.py    APScheduler job definitions
│   │   ├── alembic/            Database migrations
│   │   └── tests/              65 tests
│   └── web/                    Next.js 14 App Router frontend
│       ├── app/
│       │   ├── page.tsx              Article feed with category/source filter
│       │   ├── article/[id]/page.tsx Article detail
│       │   └── subscribe/page.tsx    Subscription form
│       ├── components/
│       └── lib/api.ts          Typed API client
├── .github/workflows/
│   ├── scheduled_fetch.yml     Runs every 2h
│   └── scheduled_digest.yml    Runs daily + Monday
├── docker-compose.yml
├── render.yaml                 Reference config (Render was set up manually)
├── run-local.sh                Local dev entrypoint
└── .env.example
```
