#!/usr/bin/env bash
set -euo pipefail

need() { command -v "$1" >/dev/null 2>&1 || return 1; }

echo "▶ Verificando herramientas..."
need python3 || { echo "❌ falta python3"; exit 1; }
if ! need kubectl && ! need oc; then
  echo "❌ falta kubectl u oc"; exit 1
fi
need kustomize || { echo "❌ falta kustomize"; exit 1; }
echo "✅ Herramientas ok"

echo "▶ Verificando versión de kustomize..."
kustomize version || true

echo "▶ Verificando acceso a clúster..."
if kubectl version --short >/dev/null 2>&1; then
  echo "✅ kubectl ok"
elif oc version >/dev/null 2>&1; then
  echo "✅ oc ok"
else
  echo "❌ no hay acceso a clúster"; exit 1
fi

echo "▶ Verificando archivos clave..."
test -f tools/gitops-lite/gitops-lite.py || { echo "❌ falta gitops-lite.py"; exit 1; }
echo "✅ Todo listo"
