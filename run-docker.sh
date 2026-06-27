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
echo -e "${GREEN}╔═══════════════════════════════╗${NC}"
echo -e "${GREEN}║   AI Digest — Docker Compose  ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Prerequisites ────────────────────────────────────────────────────────────
info "Checking prerequisites..."

if ! command -v docker &>/dev/null; then
  err "Docker is not installed. See https://docs.docker.com/get-docker/"
  exit 1
fi

if ! docker info &>/dev/null; then
  err "Docker daemon is not running. Start Docker Desktop or the Docker service."
  exit 1
fi

if ! docker compose version &>/dev/null 2>&1; then
  err "Docker Compose v2 not available. Update Docker Desktop or install the Compose plugin."
  exit 1
fi

ok "Docker and Docker Compose available"

# ── Environment ──────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  warn "No .env found. Creating from .env.example..."
  cp .env.example .env
  warn "Edit .env with your values (RESEND_API_KEY, ADMIN_SECRET, etc.) then re-run."
  exit 0
fi

mkdir -p data

# ── Build and start ──────────────────────────────────────────────────────────
info "Building and starting services (may take a few minutes on first run)..."
docker compose up --build -d

# ── Wait for API ─────────────────────────────────────────────────────────────
info "Waiting for API to be ready..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health &>/dev/null; then
    ok "API is up"
    break
  fi
  sleep 2
  if [ "$i" -eq 30 ]; then
    err "API failed to start within 60 seconds."
    err "Check logs: docker compose logs api"
    exit 1
  fi
done

# ── Ollama model ─────────────────────────────────────────────────────────────
OLLAMA_MODEL=$(grep "^OLLAMA_MODEL=" .env 2>/dev/null | cut -d= -f2 | tr -d '"' || echo "")
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2}"

info "Checking Ollama model ($OLLAMA_MODEL)..."
if docker compose exec ollama ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
  ok "Ollama model already present"
else
  info "Pulling Ollama model: $OLLAMA_MODEL (may take several minutes)..."
  docker compose exec ollama ollama pull "$OLLAMA_MODEL"
  ok "Model ready"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
ok "Services running:"
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null \
  || docker compose ps
echo ""
ok "API  → http://localhost:8000"
ok "Docs → http://localhost:8000/docs"
ok "Web  → http://localhost:3000"
echo ""
info "Useful commands:"
info "  Stop all:    docker compose down"
info "  View logs:   docker compose logs -f"
info "  Restart API: docker compose restart api"
info "  API shell:   docker compose exec api bash"
echo ""

ADMIN_SECRET=$(grep "^ADMIN_SECRET=" .env 2>/dev/null | cut -d= -f2 | tr -d '"' || echo "")
if [ -n "$ADMIN_SECRET" ]; then
  info "Trigger first news fetch:"
  info "  curl -X POST http://localhost:8000/admin/fetch -H 'X-Admin-Key: $ADMIN_SECRET'"
  echo ""
fi
