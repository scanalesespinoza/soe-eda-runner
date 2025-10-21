#!/usr/bin/env bash
set -euo pipefail
OVERLAY="${1:-dev}"

echo "⚠️ Esto eliminará recursos etiquetados gitops-lite=managed en $OVERLAY"
read -p "Confirmar (yes/NO): " ans
[[ "$ans" == "yes" ]] || { echo "Cancelado"; exit 1; }

python3 tools/gitops-lite/gitops-lite.py apply \
  --path "deploy-gitops/overlays/$OVERLAY" --kustomize --server-side --dry-run || true

# prune forzado (siempre limitando por label)
python3 tools/gitops-lite/gitops-lite.py prune \
  --path "deploy-gitops/overlays/$OVERLAY" --kustomize --server-side --selector gitops-lite=managed

echo "🗑️ Desinstalación (prune) realizada en '$OVERLAY'"
