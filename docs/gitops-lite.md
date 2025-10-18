# Operación con gitops-lite

## Comandos locales
- `make status` – vista Added/Changed/Same
- `make plan` – diff contra el clúster
- `make sync-dev` – aplica y prunea en dev (server-side)

## CI/CD
- PR: ejecuta **Plan (diff)** y no aplica
- Push a main: ejecuta **Sync** sobre `overlays/dev`

## Secrets
- `K8S_SERVER_DEV` y `K8S_TOKEN_DEV` en GitHub → Ambiente dev
- Repetir por `staging` y `prod` si se habilitan workflows

## RBAC
- El token corresponde al SA `gitops-lite-ci` con Role/RoleBinding de sólo el namespace.
