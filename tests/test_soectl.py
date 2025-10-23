from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.soectl import soectl


def _fake_which_factory(mapping: Dict[str, str | None]):
    def _fake_which(*candidates: str) -> str | None:
        for candidate in candidates:
            if candidate in mapping:
                return mapping[candidate]
        return None

    return _fake_which


def test_summarize_uses_kubectl_kustomize_when_binary_missing(monkeypatch: pytest.MonkeyPatch):
    """Cuando kustomize no está disponible se debe intentar con kubectl."""

    commands: list[list[str]] = []

    monkeypatch.setattr(
        soectl,
        "_which",
        _fake_which_factory({"kustomize": None, "kubectl": "/usr/bin/kubectl"}),
    )

    def fake_run(cmd, text, capture_output, check):  # type: ignore[override]
        commands.append(cmd)
        manifest = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: demo
  namespace: ns-demo
"""
        return subprocess.CompletedProcess(cmd, 0, manifest, "")

    monkeypatch.setattr(soectl.subprocess, "run", fake_run)

    summary = soectl._summarize_rendered_resources(Path("/fake/overlay"))

    assert summary == {"ns-demo": ["ConfigMap/demo"]}
    assert commands == [["/usr/bin/kubectl", "kustomize", "/fake/overlay"]]


def test_summarize_returns_empty_without_render(monkeypatch: pytest.MonkeyPatch):
    """Si no hay kustomize ni kubectl/oc, el resumen queda vacío."""

    monkeypatch.setattr(
        soectl,
        "_which",
        _fake_which_factory({"kustomize": None, "kubectl": None, "oc": None}),
    )

    summary = soectl._summarize_rendered_resources(Path("/fake/overlay"))

    assert summary == {}
