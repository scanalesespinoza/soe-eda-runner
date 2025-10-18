# Bootstrap de infraestructura base

Esta carpeta define los recursos fundamentales de SOE-EDA-RUNNER:
- Namespaces de entorno (`dev`, `staging`, `prod`).
- RBAC y ServiceAccounts para el CI/CD.
- PVCs y almacenamiento persistente.
- ConfigMaps y Secrets para la configuración de EDA y modelos.

Estos manifiestos pueden aplicarse manualmente o sincronizarse usando:

```bash
python3 tools/gitops-lite/gitops-lite.py sync \
  --path deploy-gitops/overlays/dev --kustomize --server-side
```


---

### ✅ **Definition of Done (DoD)**
- Los manifests se encuentran organizados y validados por `kustomize build`.  
- Todos los recursos (`namespaces`, `secrets`, `configmaps`, `pvcs`, `rbac`) se crean sin error en el clúster.  
- El ServiceAccount `gitops-lite-ci` puede aplicar manifiestos en `soe-eda-dev`.  
- La etiqueta `gitops-lite: managed` está presente en todos los recursos.  
- El entorno `dev` queda listo para despliegues en la siguiente iteración.

---

### ⚠️ **Validación esperada**
1. Ejecutar:
   ```bash
   kustomize build deploy-gitops/overlays/dev | kubectl apply -f -
   ```


→ Debe crear recursos correctamente.

Verificar existencia:

kubectl get ns,sa,pvc,cm,secret -n soe-eda-dev


Confirmar:

✅ PVCs en estado Bound

✅ Secrets y ConfigMaps cargados

✅ ServiceAccount y RoleBinding activos
