# Handoff Document

## Last Updated
2026-06-28

## Project
AI Digest — full-stack AI/ML news aggregator with email digests, deployed on Vercel (frontend) + Render (backend).

## Current State
The app is deployed and functional. The frontend (Vercel) shows articles with category/source filtering, a search bar, and a stats page with charts. The backend (Render) fetches from 15 sources every 2 hours via GitHub Actions. One known outstanding issue: the subscribe form may fail in production if `CORS_ORIGINS` on Render doesn't include the Vercel URL, or if `NEXT_PUBLIC_API_URL` wasn't set before the last Vercel build.

## What Was Done This Session
- Fixed `sqlite3.OperationalError` on startup — `mkdir -p data` now runs inside `apps/api/` before alembic
- Fixed Next.js config error — renamed `next.config.ts` → `next.config.mjs`
- Fixed deprecated `tool.uv.dev-dependencies` — migrated to `[dependency-groups] dev` in `pyproject.toml`
- Added source **categories** to the data model — migration `0001_add_source_category.py`, `category` field on `Source`, `CATEGORY_LABELS` / `CATEGORY_ORDER` in `db.py`
- Expanded sources from 5 → 15 across 5 categories (Top Stories, Research, Open Source, Company Releases, Community Buzz)
- Added category + source filter panel to homepage — category header links (`?category=X`) + source pills (`?source=X`)
- Added `/sources/categories` API endpoint
- Added `category` filter param to `/articles` endpoint
- Fixed Vercel deploy — `rootDirectory` is not valid in `vercel.json`; must be set in Vercel dashboard to `apps/web`; created `apps/web/vercel.json`
- Made `/admin/fetch` async — now fires a background task and returns `{"status":"started"}` immediately instead of hanging
- Fixed GitHub Actions workflows — added health-check retry loop before curl commands to handle Render cold starts
- Added `set -a; source .env; set +a` to `run-local.sh` so child processes (Next.js, uvicorn) inherit env vars from root `.env`
- Stripped HTML from RSS excerpts — `_strip_html()` in `fetcher.py` at fetch time; `stripHtml()` in `ArticleCard.tsx` and `article/[id]/page.tsx` for existing data
- Fixed failing test `test_admin_fetch_authorized` — updated to match new `{"status":"started"}` response
- Fixed all `datetime.utcnow()` deprecation warnings across `models.py`, `digest.py`, `fetcher.py`, `main.py`, `test_digest.py`
- Removed unused files: `FetchButton.tsx`, `actions.ts`, `apps/api/.env.example`, root `vercel.json`
- Added **search bar** — `SearchBar.tsx` client component, debounced 300ms, updates `?q=` URL param; hides category filter panel during search
- Added `/stats` API endpoint — returns total counts, articles per source, per category, per day (last 30 days)
- Added **Stats page** (`/stats`) — stat cards + line chart (articles/day) + bar chart (by source) + donut chart (by category) using Recharts
- Added Stats link to NavBar
- Updated `README.md` and `HANDOFF.md` to reflect deployed state

## Pending Work
- Subscribe form may still be broken in production — needs `CORS_ORIGINS` on Render set to Vercel URL, and `NEXT_PUBLIC_API_URL` set in Vercel + redeployed
- GitHub Actions secrets (`API_URL`, `ADMIN_SECRET`) need to be confirmed as set
- Stats and search changes are unstaged — need a commit

## Next Steps
1. **Fix subscribe in production**: Render dashboard → Environment → set `CORS_ORIGINS=https://your-app.vercel.app`; Vercel → Settings → Environment Variables → confirm `NEXT_PUBLIC_API_URL` is set → redeploy
2. **Commit pending changes**: `apps/api/app/main.py`, `schemas.py`, `apps/web/` (search + stats + NavBar)
3. **Claude API summarization**: Replace/supplement Ollama with Anthropic API so cloud deployments get real summaries. Change is mostly in `apps/api/app/summarizer.py` — check if `SUMMARIZER_ENABLED` is false and fall back to Claude API instead of empty string
4. **Add RSS output** (`/feed.xml`) — lets users subscribe via any RSS reader without needing the email flow
5. **Admin UI** — simple password-protected page to manage sources and view digest logs without curl

## Important Context
- **Render was set up manually** (New → Web Service, not Blueprint). `render.yaml` exists but Render ignores it unless you delete the service and recreate via Blueprint. Env vars must be set manually in the Render dashboard.
- **Vercel Root Directory must be `apps/web`** — set in Vercel project settings dashboard, not in `vercel.json` (that property is invalid). `apps/web/vercel.json` contains `{"framework":"nextjs"}`.
- **`NEXT_PUBLIC_API_URL` is baked in at Next.js build time** — changing it in Vercel env vars has no effect until you trigger a new deployment.
- **Render free tier sleeps after 15 min** — GitHub Actions cron jobs include a health-check retry loop (12 attempts × 15s = 3 min) to handle cold starts before calling `/admin/fetch`.
- **Single root `.env`** — `run-local.sh` uses `set -a; source .env; set +a` to export all vars to child processes. No separate `apps/api/.env` or `apps/web/.env` needed locally.
- **Category system**: Categories defined in `db.py` as `CATEGORY_LABELS` dict and `CATEGORY_ORDER` list. New sources need a `category` key matching one of: `top_stories`, `research`, `open_source`, `company`, `community`.
- **Stats page uses Recharts** — it's a client component (`StatsCharts.tsx`). The page itself (`app/stats/page.tsx`) is a server component that fetches data and passes it as props.
- **65 tests, all passing, no deprecation warnings** (except a Starlette/httpx library warning we can't control).

## Recent Git Activity
```
5c2c5f7 Fixed tests and removed weird output from summarized cards
a9031bb Celanup
fda88b9 Added button to fetch
f23108a Updated vercel.json
51130cd Updated vercel.json
9fd6868 Updated sorting and local script to load ollama correctly, updated vercel.json
d3cfba3 Added initial version of ai_digest
```

## Session History
### 2026-06-28
Major session covering: deployment fixes (Vercel root dir, Render cold starts, CORS), source categories + 15-source expansion, background fetch, HTML stripping from excerpts, datetime deprecation cleanup, search bar, stats page with Recharts charts, full doc update.
