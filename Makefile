KUSTOMIZE_PATH ?= deploy-gitops/overlays/dev
KUBE_BIN ?= kubectl

plan:
python3 tools/gitops-lite/gitops-lite.py plan --path $(KUSTOMIZE_PATH) --kustomize

status:
python3 tools/gitops-lite/gitops-lite.py status --path $(KUSTOMIZE_PATH) --kustomize || true

sync:
python3 tools/gitops-lite/gitops-lite.py sync --path $(KUSTOMIZE_PATH) --kustomize --server-side --enable-prune

apply:
python3 tools/gitops-lite/gitops-lite.py apply --path $(KUSTOMIZE_PATH) --kustomize --server-side

prune:
python3 tools/gitops-lite/gitops-lite.py prune --path $(KUSTOMIZE_PATH) --kustomize --server-side --selector gitops-lite=managed

validate:
python3 tools/gitops-lite/gitops-lite.py validate --path $(KUSTOMIZE_PATH) --kustomize

# shortcuts por entorno
sync-dev:
$(MAKE) sync KUSTOMIZE_PATH=deploy-gitops/overlays/dev

sync-staging:
$(MAKE) sync KUSTOMIZE_PATH=deploy-gitops/overlays/staging

sync-prod:
$(MAKE) sync KUSTOMIZE_PATH=deploy-gitops/overlays/prod
