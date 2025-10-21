#!/usr/bin/env bash
set -euo pipefail
OVERLAY="${1:-dev}"

echo "▶ Cargando .env (si existe)"; [ -f .env ] && source .env || true

echo "▶ Prerrequisitos"
scripts/check-prereqs.sh

echo "▶ Bootstrap $OVERLAY"
python3 tools/soectl/soectl.py init --overlay "$OVERLAY"
python3 tools/soectl/soectl.py bootstrap --overlay "$OVERLAY"

echo "▶ Sync (apply + prune)"
python3 tools/soectl/soectl.py sync --overlay "$OVERLAY" --prune

echo "✅ Instalación básica completada en overlay '$OVERLAY'"
