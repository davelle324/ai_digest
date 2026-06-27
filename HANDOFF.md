# AI Digest — Project Handoff

Last updated: 2026-06-27

This document captures everything needed to understand, continue, or hand off this project to a new developer or a future AI session.

---

## What This Is

AI Digest is a full-stack web application that:
1. Automatically fetches AI/ML news from RSS feeds (arXiv, The Batch, Towards Data Science) and HackerNews every 2 hours
2. Optionally summarizes each article using a local Ollama LLM (disabled in cloud, works locally)
3. Displays all articles on a public Next.js website (no login required)
4. Sends daily or weekly email digests to opted-in subscribers via Resend
5. Uses double opt-in email confirmation and one-click unsubscribe

---

## Current State

The project was built from scratch in a single session. All code is complete and functional. It has not yet been deployed to production — that's the next step.

**What works locally:**
- FastAPI backend with all routes
- Next.js frontend (article feed, article detail, subscribe page)
- RSS + HackerNews fetching
- Ollama summarization (if Ollama is running locally)
- APScheduler for automatic fetching and digest sending
- Resend email (if API key configured)
- Docker Compose setup

**What's ready for cloud deploy:**
- `render.yaml` for Render.com backend deployment
- `vercel.json` for Vercel frontend deployment
- GitHub Actions workflows for scheduled fetch + digest triggers
- `SUMMARIZER_ENABLED` env var flag to disable Ollama on cloud

---

## Architecture

```
GitHub repo
  ├── Vercel           → Next.js frontend (public, SSR)
  └── Render           → FastAPI backend (API + scheduler)
        └── Neon       → PostgreSQL database (persistent)

GitHub Actions cron
  ├── Every 2h         → POST /admin/fetch
  ├── Daily 08:00 UTC  → POST /admin/digest/daily
  └── Mon 08:00 UTC    → POST /admin/digest/weekly

Local dev only:
  └── Ollama           → Local LLM summarization
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.111+, Uvicorn, Python 3.11+, uv |
| Frontend | Next.js 14 App Router, TypeScript, Tailwind CSS |
| Database (local/dev) | SQLite via SQLAlchemy 2.0 + Alembic |
| Database (cloud) | Neon (serverless PostgreSQL) |
| News fetching | feedparser (RSS), httpx (HackerNews API) |
| AI summaries | Ollama (local only), disabled in cloud |
| Email | Resend Python SDK |
| Scheduler | APScheduler (in-process) + GitHub Actions cron (cloud) |
| Security | slowapi rate limiting, X-Admin-Key header, html.escape for email XSS prevention |
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
│   │   │   ├── schemas.py      Pydantic v2 request/response schemas
│   │   │   ├── db.py           DB engine, get_db dependency, init_db() with source seeding
│   │   │   ├── fetcher.py      RSS (feedparser) + HackerNews fetcher with deduplication
│   │   │   ├── summarizer.py   Ollama HTTP client; returns "" if SUMMARIZER_ENABLED=false
│   │   │   ├── digest.py       HTML email builder (html.escape'd), Resend sender, digest runners
│   │   │   └── scheduler.py    APScheduler jobs: fetch/2h, summarize/30min, digests
│   │   ├── alembic/            DB migrations (run: uv run alembic upgrade head)
│   │   ├── pyproject.toml      uv project: fastapi, sqlalchemy, feedparser, httpx, apscheduler,
│   │   │                       resend, slowapi, psycopg2-binary, pydantic[email]
│   │   └── .env.example
│   └── web/
│       ├── app/
│       │   ├── page.tsx              Home feed (SSR, revalidate 60s, paginated)
│       │   ├── article/[id]/page.tsx Article detail (SSR)
│       │   └── subscribe/page.tsx    Subscribe form shell
│       ├── components/
│       │   ├── NavBar.tsx            Server component, no auth
│       │   ├── ArticleCard.tsx       Title, source, date, excerpt, "Read more" link
│       │   └── SubscribeForm.tsx     Client component, calls POST /subscribe
│       ├── lib/api.ts                Typed fetch helpers (getArticles, getArticle, etc.)
│       └── package.json              Next.js 14.2, React 18, Tailwind 3.4
├── .github/workflows/
│   ├── scheduled_fetch.yml     Cron: every 2h → POST /admin/fetch (needs API_URL, ADMIN_SECRET secrets)
│   └── scheduled_digest.yml    Cron: 08:00 UTC → daily; Mon only → weekly
├── docker-compose.yml          Services: api (8000), web (3000), ollama (internal only)
├── render.yaml                 Render.com IaC config (reads render.yaml on Blueprint deploy)
├── vercel.json                 Vercel project config (points at apps/web)
├── .env.example                Root env template (covers both api and web vars)
└── HANDOFF.md                  This file
```

---

## Environment Variables

| Variable | Where set | Description |
|---|---|---|
| `DATABASE_URL` | API | `sqlite:///./data/digest.db` locally; Neon connection string in cloud |
| `OLLAMA_URL` | API | `http://localhost:11434` locally; not needed in cloud |
| `OLLAMA_MODEL` | API | `llama3.2` — any Ollama-compatible model |
| `SUMMARIZER_ENABLED` | API | `true` locally, `false` in cloud |
| `RESEND_API_KEY` | API | From resend.com — needed for email sending |
| `RESEND_FROM` | API | Sender email (must be a verified domain on Resend) |
| `SITE_URL` | API | Frontend URL — used in confirmation/unsubscribe links |
| `CORS_ORIGINS` | API | Comma-separated list of allowed frontend origins |
| `ADMIN_SECRET` | API | Shared secret for X-Admin-Key header on /admin/* endpoints |
| `NEXT_PUBLIC_API_URL` | Web | Backend API base URL (must be set at build time for Vercel) |
| `API_URL` | GitHub Secrets | Render service URL for cron jobs |
| `ADMIN_SECRET` | GitHub Secrets | Same value as backend ADMIN_SECRET |

---

## API Routes

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | Returns `{"status":"ok"}` |
| GET | `/sources` | None | List enabled news sources |
| GET | `/articles` | None | Paginated articles (`?page=1&limit=20&source_id=`) |
| GET | `/articles/{id}` | None | Single article detail |
| POST | `/subscribe` | None | Create subscription (rate-limited 5/min per IP) |
| GET | `/confirm/{token}` | Token | Confirm subscription, redirect to frontend |
| GET | `/unsubscribe/{token}` | Token | Unsubscribe |
| POST | `/admin/fetch` | X-Admin-Key | Trigger news fetch |
| POST | `/admin/summarize` | X-Admin-Key | Summarize up to 20 pending articles |
| POST | `/admin/digest/daily` | X-Admin-Key | Trigger daily digest send |
| POST | `/admin/digest/weekly` | X-Admin-Key | Trigger weekly digest send |

---

## Default News Sources (seeded automatically)

| Name | Type |
|---|---|
| arXiv cs.AI | RSS |
| arXiv cs.LG | RSS |
| The Batch (deeplearning.ai) | RSS |
| Towards Data Science | RSS |
| HackerNews AI | HN API (keyword-filtered) |

HackerNews keywords: `ai`, `ml`, `llm`, `gpt`, `machine learning`, `neural`, `deep learning`, `transformer`, `openai`, `anthropic`, `gemini`, `mistral`, `ollama`, `hugging face`, `langchain`, `rag`, `fine-tun`

---

## Cloud Deployment Steps (not done yet)

### Prerequisites
- GitHub repo pushed: `git push origin main`
- Resend account with verified domain/email
- Render account
- Neon account
- Vercel account

### Order of operations
1. **Neon**: Create project `ai-digest` → copy connection string
2. **Render**: New → Blueprint → connect repo → Render reads `render.yaml` → deploys API
   - Set env vars manually in Render dashboard (DATABASE_URL, SITE_URL, CORS_ORIGINS, RESEND_*)
   - Copy the Render service URL
3. **Vercel**: Import repo → Vercel reads `vercel.json` → set `NEXT_PUBLIC_API_URL` → deploy
   - Copy the Vercel URL
   - Go back to Render → set SITE_URL and CORS_ORIGINS to the Vercel URL → redeploy
4. **GitHub Secrets**: Settings → Secrets → Actions → add `API_URL` and `ADMIN_SECRET`
5. **Verify**: `curl https://your-render-url.onrender.com/health`
6. **First fetch**: `curl -X POST .../admin/fetch -H "X-Admin-Key: your-secret"`

---

## Known Limitations

1. **Render free tier sleeps** after 15 min of no traffic. GitHub Actions cron wakes it for scheduled jobs, but if someone subscribes at an odd time and the server is asleep, the first request takes ~30s to wake.
2. **No summaries in cloud** — Ollama needs GPU/high RAM. Articles show the first ~500 chars as excerpt instead.
3. **Neon free tier**: 0.5 GB storage, 190 compute hours/month. For an AI news digest this should be fine for months.
4. **APScheduler is in-process**: If the Render service is restarted, the scheduler restarts too. For critical jobs, GitHub Actions is the backup. Don't run multiple Render instances (scheduler would run N times).
5. **SQLite on local**: Data stored in `apps/api/data/digest.db`. Not tracked in git.
6. **No admin UI**: Managing sources, viewing digest logs, or forcing specific article re-summarization requires direct DB access or curl commands.
7. **HackerNews keyword filter**: Very broad — will catch some non-AI stories. Could be refined.

---

## Security Notes

- Admin endpoints require `X-Admin-Key: {ADMIN_SECRET}` header
- Email HTML is escaped with `html.escape()` to prevent XSS from malicious RSS feeds
- Subscribe endpoint is rate-limited (5/minute per IP via slowapi)
- Subscriber emails are masked in logs (`jo***@example.com`)
- Ollama port is NOT exposed to host in Docker Compose (internal network only)
- All secrets are env vars only — nothing hardcoded

---

## Future Ideas / Roadmap

### Near-term
- [ ] **Admin UI** — simple password-protected dashboard to manage sources, view subscriber counts, see digest logs, force re-fetch
- [ ] **More news sources** — MIT News, Google AI Blog, Hugging Face blog, AI Alignment Forum RSS
- [ ] **Category tagging** — tag articles by topic (LLMs, computer vision, RL, safety, etc.) and let subscribers filter
- [ ] **Claude API summarization** — instead of/alongside Ollama; enables summaries in cloud without GPU

### Medium-term
- [ ] **Search** — full-text search across article titles and summaries (SQLite FTS5 or Postgres pg_tsvector)
- [ ] **Subscriber preferences** — let users choose topic categories for their digest
- [ ] **Digest preview** — web page at `/digest/preview` showing what today's digest would look like
- [ ] **Click tracking** — track which articles subscribers click in emails (optional analytics)
- [ ] **Unsubscribe reason** — ask why they unsubscribed (optional one-question survey)

### Long-term
- [ ] **Multiple digest templates** — newsletter-style, plain text, ultra-brief (titles only)
- [ ] **Social sharing** — share button on article pages
- [ ] **RSS output** — expose a `/feed.xml` so the digest itself can be subscribed to via any RSS reader
- [ ] **AI-generated digest intro** — a 2-3 sentence "this week in AI" lede written by Claude

---

## Running Locally (Quick Reference)

```bash
# Backend
cd apps/api
cp .env.example .env          # fill in RESEND_API_KEY, ADMIN_SECRET
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend (separate terminal)
cd apps/web
npm install
npm run dev

# Pull Ollama model (separate terminal, if you want summaries)
ollama pull llama3.2

# Trigger first fetch
curl -X POST http://localhost:8000/admin/fetch \
  -H "X-Admin-Key: your-admin-secret"
```

---

## Picking Up This Project

If you're a future developer (or AI session) picking this up:

1. Read this file first
2. Read `README.md` for usage instructions
3. The code is complete — the main outstanding task is **deploying to cloud** (steps in the Cloud Deployment section above)
4. Key files to understand: `apps/api/app/main.py` (routes), `apps/api/app/fetcher.py` (how articles are collected), `apps/api/app/digest.py` (how emails are sent)
5. The `.env.example` at the root covers all required variables
6. To add a news source: edit `DEFAULT_SOURCES` in `apps/api/app/db.py`
7. To test email sending locally: set `RESEND_API_KEY` and call `POST /admin/digest/daily`
