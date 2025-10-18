# Guía de contribución

Este repositorio utiliza un enfoque GitOps y modular.
Las contribuciones deben seguir la estructura de carpetas y convenciones establecidas.

## Reglas básicas
- Usa **pull requests** con descripción clara.
- Toda nueva funcionalidad debe incluir documentación en `docs/`.
- Los manifiestos Kubernetes deben estar en `deploy-gitops/` y renderizar correctamente con `kustomize build`.
- Los cambios en imágenes deben pasar por CI antes de sincronizar al clúster.

## Branching model
- `main` → estable y desplegable.
- `feature/*` → nuevas funcionalidades o servicios.
- `fix/*` → correcciones menores.

## Contacto
Responsable técnico: Sergio Canales  
Email: <contact@scanale.com>
