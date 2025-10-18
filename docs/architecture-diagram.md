# Arquitectura general de SOE-EDA-RUNNER



[ Dataset ]
↓
[ EDA / Train Worker (Python) ]
↓
[ Artifacts / Reports / Models (S3) ]
↓
[ Integration API (Quarkus) ]
↓
[ Presentation UI (Qute) ]
↓
[ Promotion to Inference Service (Python) ]


**Principios:**
- Arquitectura modular y desacoplada.
- GitOps como fuente de verdad.
- Infraestructura reproducible.
- Promoción controlada entre ambientes.
