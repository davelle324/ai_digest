# AI Digest — Project Handoff

Last updated: 2026-06-28

This document captures everything needed to understand, continue, or hand off this project to a new developer or future AI session.

---

## What This Is

AI Digest is a full-stack web application that:
1. Automatically fetches AI/ML news from 15 curated RSS feeds and HackerNews every 2 hours
2. Optionally summarizes each article using a local Ollama LLM (disabled in cloud, works locally)
3. Displays all articles on a public Next.js website with category and source filtering
4. Sends daily or weekly email digests to opted-in subscribers via Resend
5. Uses double opt-in email confirmation and one-click unsubscribe

---

## Current State

The project is **deployed and running** in production.

| Service | Platform | URL |
|---|---|---|
| Frontend | Vercel | Vercel auto-assigns a `.vercel.app` domain |
| Backend API | Render (Web Service, free tier) | Render auto-assigns an `.onrender.com` domain |
| Database | User-managed (SQLite locally, Neon in cloud) | — |

**Deployment notes:**
- Render was set up via **New → Web Service** (not Blueprint). `render.yaml` exists but is not used by Render — it's documentation/future reference only.
- Vercel Root Directory must be set to `apps/web` in the Vercel dashboard (project → Settings → General → Root Directory). The `apps/web/vercel.json` holds the framework config.
- GitHub Actions secrets `API_URL` and `ADMIN_SECRET` must be set for scheduled jobs to work.

**What's working:**
- Article fetching from all 15 sources every 2 hours (via GitHub Actions cron)
- Category and source filtering on the frontend
- Subscribe/confirm/unsubscribe flow
- Daily + weekly digest emails via Resend + GitHub Actions
- GitHub Actions health-check retry (handles Render cold starts)
- HTML stripping from RSS excerpts (both at fetch time and on display)

**Known outstanding issue:**
- Subscribe form may fail with "failed to fetch" if `NEXT_PUBLIC_API_URL` is not set in Vercel or if `CORS_ORIGINS` on Render doesn't include the Vercel domain. Both must match.

---

## Architecture

```
GitHub repo
  ├── Vercel           → Next.js frontend (public, SSR, Root Directory: apps/web)
  └── Render           → FastAPI backend (API + in-process scheduler)
        └── Database   → SQLite locally / Neon PostgreSQL in cloud

GitHub Actions cron
  ├── Every 2h         → wake API (/health retry) → POST /admin/fetch
  ├── Daily 08:00 UTC  → wake API → POST /admin/digest/daily
  └── Mon 08:00 UTC    → wake API → POST /admin/digest/weekly
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.111+, Uvicorn, Python 3.13, uv |
| Frontend | Next.js 14.2 App Router, TypeScript, Tailwind CSS |
| Database (local) | SQLite via SQLAlchemy 2.0 + Alembic |
| Database (cloud) | Neon (serverless PostgreSQL) recommended |
| News fetching | feedparser (RSS), httpx (HackerNews API) |
| AI summaries | Ollama (local only), disabled in cloud |
| Email | Resend Python SDK |
| Scheduler | APScheduler (in-process) + GitHub Actions cron (cloud) |
| Security | slowapi rate limiting, X-Admin-Key header, html.escape for email XSS |
| Containers | Docker Compose (local dev) |

---

## File Map

```
ai_digest/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py         Routes, CORS, rate limiting, lifespan startup
│   │   │   ├── models.py       SQLAlchemy models: Source, Article, Subscriber, DigestLog
│   │   │   ├── schemas.py      Pydantic v2 schemas (SourceOut includes category)
│   │   │   ├── db.py           DB engine, DEFAULT_SOURCES (15 sources w/ categories),
│   │   │   │                   CATEGORY_LABELS, CATEGORY_ORDER, init_db()
│   │   │   ├── fetcher.py      RSS (feedparser) + HackerNews fetcher; strips HTML from excerpts
│   │   │   ├── summarizer.py   Ollama HTTP client; returns "" if SUMMARIZER_ENABLED=false
│   │   │   ├── digest.py       HTML email builder (html.escape'd), Resend sender
│   │   │   └── scheduler.py    APScheduler: fetch/2h, summarize/30min, digests
│   │   ├── alembic/
│   │   │   └── versions/
│   │   │       └── 0001_add_source_category.py  Adds category column (idempotent)
│   │   ├── tests/              65 tests, all passing, no warnings
│   │   └── pyproject.toml      dependency-groups.dev (not tool.uv.dev-dependencies)
│   └── web/
│       ├── app/
│       │   ├── page.tsx              Home feed: category + source filter panel, paginated grid
│       │   ├── article/[id]/page.tsx Article detail with HTML-stripped summary/excerpt
│       │   └── subscribe/page.tsx    Subscribe form shell
│       ├── components/
│       │   ├── NavBar.tsx
│       │   ├── ArticleCard.tsx       Strips HTML from excerpt/summary before display
│       │   └── SubscribeForm.tsx     Client component → POST /subscribe
│       ├── lib/api.ts                getArticles(page, limit, sourceId, category),
│       │                             getSources(), getCategories()
│       ├── next.config.mjs           (not .ts — older Next.js version)
│       └── vercel.json               {"framework": "nextjs"}
├── .github/workflows/
│   ├── scheduled_fetch.yml     Cron every 2h: health retry → POST /admin/fetch
│   └── scheduled_digest.yml    Cron 08:00 UTC: health retry → daily/weekly digest
├── docker-compose.yml
├── render.yaml                 Reference only — Render was set up manually
├── run-local.sh                Recommended local dev entrypoint (sources .env, starts both services)
└── .env.example                Single root env file covers all variables
```

---

## Environment Variables

| Variable | Where needed | Description |
|---|---|---|
| `DATABASE_URL` | Render | `sqlite:///./data/digest.db` locally; Neon URL in cloud |
| `OLLAMA_URL` | Render/local | `http://localhost:11434` locally; unused in cloud |
| `OLLAMA_MODEL` | Render/local | `llama3.2` default |
| `SUMMARIZER_ENABLED` | Render | Set `false` in cloud (no GPU) |
| `RESEND_API_KEY` | Render | From resend.com |
| `RESEND_FROM` | Render | Verified sender address |
| `SITE_URL` | Render | Vercel frontend URL (for confirmation/unsubscribe links in emails) |
| `CORS_ORIGINS` | Render | Must include the Vercel URL e.g. `https://your-app.vercel.app` |
| `ADMIN_SECRET` | Render + GitHub Secrets | Secret for X-Admin-Key on /admin/* endpoints |
| `NEXT_PUBLIC_API_URL` | Vercel | Render service URL — **baked in at build time**, redeploy after changing |
| `API_URL` | GitHub Secrets | Render service URL for Actions cron |

---

## API Routes

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | `{"status":"ok"}` |
| GET | `/sources` | None | List enabled sources sorted by category order |
| GET | `/sources/categories` | None | List category keys and display labels |
| GET | `/articles` | None | Paginated (`?page&limit&source_id&category`) |
| GET | `/articles/{id}` | None | Single article detail |
| POST | `/subscribe` | None | Create subscription (rate-limited 5/min per IP) |
| GET | `/confirm/{token}` | Token | Confirm subscription, redirect to frontend |
| GET | `/unsubscribe/{token}` | Token | Unsubscribe |
| POST | `/admin/fetch` | X-Admin-Key | Kick off background fetch (returns immediately) |
| POST | `/admin/summarize` | X-Admin-Key | Summarize up to 20 pending articles |
| POST | `/admin/digest/daily` | X-Admin-Key | Trigger daily digest send |
| POST | `/admin/digest/weekly` | X-Admin-Key | Trigger weekly digest send |

---

## News Sources (15 total, seeded automatically)

| Category | Name | Type |
|---|---|---|
| 🔥 Top Stories | OpenAI Blog | RSS |
| 🔥 Top Stories | Anthropic | RSS |
| 🔥 Top Stories | Google AI | RSS |
| 🔥 Top Stories | TechCrunch AI | RSS |
| 🔥 Top Stories | The Batch (DeepLearning.AI) | RSS |
| 🧠 Research | arXiv cs.AI | RSS |
| 🧠 Research | arXiv cs.LG | RSS |
| 🧠 Research | arXiv cs.CL | RSS |
| 💻 Open Source | Hugging Face | RSS |
| 💻 Open Source | Towards Data Science | RSS |
| 🏢 Company Releases | NVIDIA Blog | RSS |
| 🏢 Company Releases | Meta AI | RSS |
| 👥 Community Buzz | HackerNews AI | HN API (keyword-filtered) |
| 👥 Community Buzz | Reddit r/MachineLearning | RSS |
| 👥 Community Buzz | Reddit r/LocalLLaMA | RSS |

To add a source: add an entry to `DEFAULT_SOURCES` in `apps/api/app/db.py` with a `category` field matching one of the keys in `CATEGORY_LABELS`.

---

## Running Locally

```bash
# One command starts everything
./run-local.sh
```

This script: checks prerequisites, exports all `.env` vars to child processes, creates the data dir, runs Alembic migrations, starts FastAPI on :8000, starts Next.js on :3000.

To trigger a manual fetch:
```bash
curl -X POST http://localhost:8000/admin/fetch \
  -H "X-Admin-Key: your-admin-secret"
```

---

## Known Limitations

1. **Render free tier sleeps** after 15 min of inactivity. GitHub Actions wakes it for scheduled jobs (health retry loop), but ad-hoc requests may hit a ~30s cold start.
2. **No summaries in cloud** — Ollama needs GPU/high RAM. Articles show excerpts only in cloud.
3. **APScheduler is in-process** — if Render restarts, the scheduler restarts. GitHub Actions is the reliable backup for scheduled work.
4. **Render set up manually** — `render.yaml` exists but Render won't read it unless the service is deleted and recreated via Blueprint.
5. **No admin UI** — managing sources or viewing digest logs requires direct DB access or curl.
6. **HackerNews keyword filter** — broad, catches some non-AI stories.

---

## Suggested Next Steps

### Immediate (deployment health)
- Verify `CORS_ORIGINS` on Render includes the Vercel URL — fixes subscribe form
- Verify `NEXT_PUBLIC_API_URL` is set in Vercel and the app was redeployed after setting it
- Confirm GitHub Actions secrets `API_URL` and `ADMIN_SECRET` are set and Actions are running

### Near-term features
- **Claude API summarization** — replace/supplement Ollama with the Anthropic API; enables summaries in cloud without GPU
- **Admin UI** — simple password-protected dashboard to manage sources, view subscriber counts, force re-fetch
- **RSS output** — expose `/feed.xml` so the digest can be subscribed to via any RSS reader

### Medium-term
- **Search** — full-text search across titles and summaries (SQLite FTS5 or Postgres `pg_tsvector`)
- **Subscriber topic preferences** — let users pick categories for their digest
- **Digest preview page** — web page showing what today's digest would look like

---

## Picking Up This Project

1. Read this file
2. Read `README.md` for usage
3. Run `./run-local.sh` to start locally
4. Key files: `apps/api/app/main.py` (routes), `apps/api/app/fetcher.py` (collection), `apps/api/app/db.py` (sources + categories), `apps/api/app/digest.py` (email)
5. Tests: `cd apps/api && uv run pytest` — 65 tests, all pass
