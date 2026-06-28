#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[info]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ok]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $*"; }
err()   { echo -e "${RED}[error]${NC} $*"; }

echo ""
echo -e "${GREEN}╔══════════════════════════╗${NC}"
echo -e "${GREEN}║   AI Digest — Local Dev  ║${NC}"
echo -e "${GREEN}╚══════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Prerequisites ────────────────────────────────────────────────────────────
info "Checking prerequisites..."

if ! command -v uv &>/dev/null; then
  err "uv is not installed. Install from https://docs.astral.sh/uv/"
  exit 1
fi

if ! command -v node &>/dev/null; then
  err "Node.js is not installed. Install from https://nodejs.org/"
  exit 1
fi

OLLAMA_AVAILABLE=false
if command -v ollama &>/dev/null; then
  OLLAMA_AVAILABLE=true
  ok "uv, node, ollama found"
else
  warn "Ollama not found — AI summaries disabled (articles show excerpts only)"
  ok "uv, node found"
fi

# ── Environment ──────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  warn "No .env found. Creating from .env.example..."
  cp .env.example .env
  warn "Edit .env with your values (RESEND_API_KEY, ADMIN_SECRET, etc.) then re-run."
  exit 0
fi

# ── Ollama model ─────────────────────────────────────────────────────────────
if $OLLAMA_AVAILABLE; then
  OLLAMA_MODEL=$(grep "^OLLAMA_MODEL=" .env 2>/dev/null | cut -d= -f2 | tr -d '"' || echo "")
  OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2}"
  if ! pgrep -x ollama >/dev/null 2>&1; then
    echo "Starting Ollama..."
    ollama serve >/dev/null 2>&1 &
    sleep 2
  fi
  if ! ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
    info "Pulling Ollama model: $OLLAMA_MODEL ..."
    ollama pull "$OLLAMA_MODEL"
  else
    ok "Ollama model ($OLLAMA_MODEL) already present"
  fi
fi

# ── Start API ────────────────────────────────────────────────────────────────
info "Starting FastAPI backend..."
cd "$SCRIPT_DIR/apps/api"
mkdir -p data
uv sync --quiet
uv run alembic upgrade head --quiet 2>/dev/null || uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000 --log-level warning &
API_PID=$!
cd "$SCRIPT_DIR"

info "Waiting for API to be ready..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:8000/health &>/dev/null; then
    ok "API is up"
    break
  fi
  sleep 1
  if [ "$i" -eq 20 ]; then
    err "API failed to start within 20 seconds. Check for errors above."
    kill "$API_PID" 2>/dev/null || true
    exit 1
  fi
done

# ── Start Web ────────────────────────────────────────────────────────────────
info "Starting Next.js frontend..."
cd "$SCRIPT_DIR/apps/web"
if [ ! -d node_modules ]; then
  npm install --silent
fi
npm run dev -- --port 3000 &
WEB_PID=$!
cd "$SCRIPT_DIR"

echo ""
ok "API  → http://localhost:8000"
ok "Docs → http://localhost:8000/docs"
ok "Web  → http://localhost:3000"
echo ""

ADMIN_SECRET=$(grep "^ADMIN_SECRET=" .env 2>/dev/null | cut -d= -f2 | tr -d '"' || echo "")
if [ -n "$ADMIN_SECRET" ]; then
  info "Trigger a news fetch:"
  info "  curl -X POST http://localhost:8000/admin/fetch -H 'X-Admin-Key: $ADMIN_SECRET'"
  echo ""
fi

warn "Press Ctrl+C to stop all services"

# ── Cleanup ──────────────────────────────────────────────────────────────────
cleanup() {
  echo ""
  info "Shutting down..."
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
  wait "$API_PID" "$WEB_PID" 2>/dev/null || true
  ok "Stopped."
}

trap cleanup EXIT INT TERM
wait
