# SOE-EDA-RUNNER

SOE-EDA-RUNNER es un entorno estandarizado para realizar análisis exploratorios de datos (EDA) y entrenamientos de modelos de Machine Learning, diseñado para ser **portable, promovible y reproducible** sobre Kubernetes/OpenShift.

## Objetivo
Proveer un ciclo completo:
**Dataset → EDA → Entrenamiento → Promoción a servicio → Inferencia → Reentrenamiento**

## Tecnologías
- **Python 3.11** – EDA y entrenamiento
- **Quarkus (Java 21)** – Orquestación e interfaces
- **OpenShift / Kubernetes** – Plataforma de ejecución
- **GitHub Actions** – CI/CD
- **GitOps Lite** – Sincronización declarativa de manifiestos

## Estructura general
- `app/` – Servicios de aplicación (EDA worker, inferencia, integración, UI)
- `ml/` – Pipelines y artefactos de análisis y modelos
- `deploy-gitops/` – Manifiestos Kubernetes
- `tools/` – Utilitarios (como gitops-lite)
- `.github/workflows/` – CI/CD y automatización
- `docs/` – Diagramas y documentación técnica
