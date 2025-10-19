# EDA Runner (servicio + job)

## Servicio HTTP
- **POST** `/eda/run`
```json
{
  "dataset_path": "/data/insurance.csv",
  "output_path": "/out",
  "outliers_col": "charges"
}
```

Respuesta:

```
{ "runId":"abcd1234","status":"SUCCESS","summary":{...} }
```

Los artefactos quedan en `/out/<runId>/`.

## Job batch

Editar `deploy-gitops/base/eda-worker/job-template.yaml` y sincronizar:

```
python3 tools/gitops-lite/gitops-lite.py sync \
  --path deploy-gitops/overlays/dev --kustomize --server-side --enable-prune
```

---

## Validación

1. **Build local**
   ```bash
   docker build -t eda-worker:test app/eda-train-worker
   ```

2. **Despliegue dev**
   ```bash
   python3 tools/gitops-lite/gitops-lite.py sync \
     --path deploy-gitops/overlays/dev --kustomize --server-side --enable-prune
   kubectl get deploy,svc,route -n soe-eda-dev
   ```

3. **Probar API**
   ```bash
   curl -X POST "https://<ROUTE>/eda/run" \
     -H "Content-Type: application/json" \
     -d '{"dataset_path":"/data/insurance.csv","output_path":"/out","outliers_col":"charges"}'
   ```

4. **Verificar artefactos**
   ```bash
   kubectl exec -n soe-eda-dev deploy/eda-worker -- ls -la /out
   ```

5. **Ejecutar Job**
   ```bash
   # Editar job-template.yaml si usas otra ruta de dataset y sync.
   kubectl logs job/<job-name> -n soe-eda-dev
   ```

✅ **Definition of Done (DoD)**

- Imagen `eda-train-worker` se construye y publica vía GHA.
- Deployment + Service + Route del worker listos en dev.
- Job plantilla funcional con artefactos en `/out/<timestamp>/`.
- Artefactos generados: `eda-report.html`, `eda-summary.json`, `outliers.csv`, `plots/*`.
- `gitops-lite` plan/sync aplica sin errores.

⚠️ **Notas**

- En OpenShift, asegúrate de que la ServiceAccount tenga permisos y que las PVCs estén en estado Bound.
- Para S3/MinIO, en iteración 5 añadiremos ingestión/descarga; de momento trabajamos con PVC (`/data` y `/out`).
- Si usas restricciones de seguridad estrictas, añade `runAsNonRoot` y `fsGroup` en el Deployment.
