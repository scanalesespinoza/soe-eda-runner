# Guía de instalación — SOE-EDA-RUNNER

Esta guía instala el entorno sobre OpenShift/Kubernetes con CI/CD (GitHub Actions) y GitOps Lite.

## Requisitos
- kubectl u oc
- kustomize ≥ v5
- python3.11
- docker/podman para build local
- Acceso al clúster (token y URL API)
- GHCR o registry con credenciales
- Secrets de GitHub para CI/CD

## Pasos rápidos
1. Clonar repo y copiar variables:
   ```bash
   cp .env.example .env && nano .env
   ```
2. Verificar prerrequisitos:
   ```bash
   scripts/check-prereqs.sh
   ```
3. Bootstrap infraestructura (namespaces, SA, RBAC, PVC, CM, Secrets):
   ```bash
   python3 tools/soectl/soectl.py init --overlay dev
   python3 tools/soectl/soectl.py bootstrap --overlay dev
   ```
4. Configurar secrets en GitHub (API server y token):
   ```bash
   scripts/set-github-secrets.sh dev
   ```
5. Sincronizar manifiestos (GitOps Lite):
   ```bash
   python3 tools/soectl/soectl.py sync --overlay dev
   ```
6. Build de imágenes base (opcional) y despliegue:
   - merge/push → workflows de build actualizan overlays → gitops-lite sync aplica.

## Validación
- `make status` — drift repo vs clúster (dev)
- `make sync-dev` — aplica cambios
- Revisar routes: integration, presentation, inference, eda-worker

### Health
```bash
curl https://<route>/q/health   # Quarkus
curl https://<route>/healthz    # FastAPI
```

## Desinstalación (solo dev)
```bash
scripts/uninstall.sh dev
```

## Troubleshooting
Revisa logs:
```bash
kubectl logs deploy/integration -n $NS
kubectl logs deploy/inference  -n $NS
```

`soectl doctor` entrega diagnóstico y sugerencias.
