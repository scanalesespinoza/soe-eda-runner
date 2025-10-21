OVERLAY ?= deploy-gitops/overlays/dev

plan:
python3 tools/gitops-lite/gitops-lite.py plan --path $(OVERLAY) --kustomize || true

status:
python3 tools/gitops-lite/gitops-lite.py status --path $(OVERLAY) --kustomize || true

sync:
python3 tools/gitops-lite/gitops-lite.py sync --path $(OVERLAY) --kustomize --server-side --enable-prune

sync-dev:  ; $(MAKE) sync OVERLAY=deploy-gitops/overlays/dev
sync-stg:  ; $(MAKE) sync OVERLAY=deploy-gitops/overlays/staging
sync-prod: ; $(MAKE) sync OVERLAY=deploy-gitops/overlays/prod

doctor:
python3 tools/soectl/soectl.py doctor
