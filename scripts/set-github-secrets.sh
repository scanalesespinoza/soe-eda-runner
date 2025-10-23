#!/usr/bin/env bash
set -euo pipefail
ENV="${1:-dev}"

if [ -z "${REPO_SLUG:-}" ] || [ -z "${K8S_SERVER_DEV:-}" ] || [ -z "${K8S_TOKEN_DEV:-}" ]; then
  if [ -f .env ]; then
    echo "ℹ️  Cargando variables desde .env"
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
  fi
fi

: "${REPO_SLUG:?exporta REPO_SLUG=org/repo}"
: "${K8S_SERVER_DEV:?}"
: "${K8S_TOKEN_DEV:?}"

echo "▶ Configurando secrets en GitHub (gh cli requerido)"
command -v gh >/dev/null || { echo "❌ falta gh (GitHub CLI)"; exit 1; }

if [ "$ENV" = "dev" ]; then
  gh secret set K8S_SERVER_DEV --repo "$REPO_SLUG" --body "$K8S_SERVER_DEV"
  gh secret set K8S_TOKEN_DEV  --repo "$REPO_SLUG" --body "$K8S_TOKEN_DEV"
fi

echo "✅ Secrets configurados para $ENV"
