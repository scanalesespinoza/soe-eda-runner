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
   # El overlay "dev" es el valor por defecto, por lo que no es obligatorio pasarlo.
   python3 tools/soectl/soectl.py init
   python3 tools/soectl/soectl.py bootstrap

   # Si necesitas un overlay distinto, utiliza la opción explícita (usa "="), por ejemplo:
   # python3 tools/soectl/soectl.py init --overlay=dev
   # python3 tools/soectl/soectl.py bootstrap --overlay=dev
   ```
4. Configurar secrets en GitHub (API server y token). El script carga automáticamente
   las variables definidas en `.env` (o puedes exportarlas manualmente):
   ```bash
   scripts/set-github-secrets.sh dev
   ```
5. Sincronizar manifiestos (GitOps Lite):
   ```bash
   # El overlay "dev" es el valor por defecto, por lo que no es obligatorio pasarlo.
   python3 tools/soectl/soectl.py sync

   # Si necesitas un overlay distinto, utiliza la opción explícita (usa "="), por ejemplo:
   # python3 tools/soectl/soectl.py sync --overlay=dev

   # Para reinstalar limpiamente puedes ejecutar un cleanup previo al apply:
   # python3 tools/soectl/soectl.py sync --overlay=dev --cleanup
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
