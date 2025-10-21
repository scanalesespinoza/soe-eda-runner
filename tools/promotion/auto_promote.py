#!/usr/bin/env python3
"""Automate promotions of model artefacts based on evaluation metrics."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import urlparse

import yaml


POLICY_PATH = Path("ml/policies/promotion.yaml")
DEFAULT_POLICY = {
    "thresholds": {"r2_min_gain": 0.01, "rmse_min_drop": 100},
    "actions": {"auto_promote": True, "target_overlay": "dev"},
}


def load_policy() -> Dict[str, Dict[str, object]]:
    if POLICY_PATH.exists():
        with open(POLICY_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        merged = DEFAULT_POLICY.copy()
        merged["thresholds"] = {**DEFAULT_POLICY["thresholds"], **(data.get("thresholds", {}))}
        merged["actions"] = {**DEFAULT_POLICY["actions"], **(data.get("actions", {}))}
        return merged
    return DEFAULT_POLICY


def load_metrics(path: str) -> Dict[str, float]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def evaluate(
    current: Dict[str, float],
    candidate: Dict[str, float],
    thresholds: Dict[str, float],
) -> Tuple[bool, Tuple[str, ...]]:
    if not candidate:
        return False, ("candidate metrics unavailable",)
    if not current:
        return True, ("no current model",)

    r2_gain = float(candidate.get("r2", 0.0)) - float(current.get("r2", 0.0))
    rmse_delta = float(candidate.get("rmse", float("inf"))) - float(current.get("rmse", float("inf")))
    rmse_drop = -rmse_delta
    improved = (
        r2_gain >= float(thresholds.get("r2_min_gain", 0.01))
        and rmse_drop >= float(thresholds.get("rmse_min_drop", 100))
    )
    reasons = (f"r2 {r2_gain:+.4f}", f"rmse {rmse_delta:+.4f}")
    return improved, reasons


def overlay_configmap(overlay_path: Path) -> Path:
    cm = overlay_path / "patches" / "inference-configmap.yaml"
    if cm.exists():
        return cm
    return overlay_path / "kustomization.yaml"


def update_configmap(path: Path, model_uri: str, model_format: str, metadata_uri: str | None) -> None:
    text = path.read_text(encoding="utf-8")
    updated = text
    if "MODEL_PATH" in text:
        updated = re.sub(r'(MODEL_PATH:\s*)".*?"', rf'\1"{model_uri}"', updated)
    if "MODEL_FORMAT" in updated:
        updated = re.sub(r'(MODEL_FORMAT:\s*)".*?"', rf'\1"{model_format}"', updated)
    if metadata_uri and "MODEL_META_PATH" in updated:
        updated = re.sub(r'(MODEL_META_PATH:\s*)".*?"', rf'\1"{metadata_uri}"', updated)

    if updated == text:
        raise RuntimeError(f"Unable to update MODEL_PATH in {path}")

    path.write_text(updated, encoding="utf-8")
    subprocess.check_call(["git", "add", str(path)])


def ensure_git_identity() -> None:
    try:
        subprocess.check_call(["git", "config", "user.name"])
        subprocess.check_call(["git", "config", "user.email"])
    except subprocess.CalledProcessError:
        subprocess.check_call(["git", "config", "user.name", os.getenv("GIT_AUTHOR_NAME", "ci-bot")])
        subprocess.check_call([
            "git",
            "config",
            "user.email",
            os.getenv("GIT_AUTHOR_EMAIL", "ci-bot@example.com"),
        ])


def record_promotion(model_uri: str, overlay: str, reasons: Tuple[str, ...], actor: str) -> None:
    parsed = urlparse(model_uri)
    if parsed.scheme != "s3":
        print("[promotion] Non-S3 URI detected, skipping promotion.json upload")
        return

    key_prefix = parsed.path.lstrip("/")
    directory = key_prefix.rsplit("/", 1)[0]
    promotion_key = f"{directory}/promotion.json"

    payload = {
        "overlay": overlay,
        "when": datetime.utcnow().isoformat() + "Z",
        "by": actor,
        "reason": ", ".join(reasons),
        "model_uri": model_uri,
    }

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except Exception as exc:  # pragma: no cover
        print(f"[promotion] boto3 unavailable, skipping promotion.json upload ({exc})")
        return

    session = boto3.session.Session(
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        region_name=os.getenv("AWS_REGION", os.getenv("S3_REGION", "us-east-1")),
    )
    client = session.client("s3", endpoint_url=os.getenv("S3_ENDPOINT"))

    try:
        client.put_object(
            Bucket=parsed.netloc,
            Key=promotion_key,
            Body=json.dumps(payload, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"[promotion] promotion.json stored at s3://{parsed.netloc}/{promotion_key}")
    except (BotoCoreError, ClientError) as exc:  # pragma: no cover
        print(f"[promotion] Failed to upload promotion.json: {exc}")


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit("Usage: auto_promote.py current.json candidate.json s3://.../model.onnx")

    current_path, candidate_path, model_uri = sys.argv[1:4]
    policy = load_policy()

    current = load_metrics(current_path)
    candidate = load_metrics(candidate_path)

    improved, reasons = evaluate(current, candidate, policy["thresholds"])

    if not improved:
        print("NOT IMPROVED: no promotion")
        return

    overlay = policy["actions"].get("target_overlay", "dev")
    overlay_path = Path("deploy-gitops") / "overlays" / overlay
    metadata_uri = None
    if model_uri.startswith("s3://"):
        directory = model_uri.rsplit("/", 1)[0]
        metadata_uri = f"{directory}/model-metadata.json"

    configmap_path = overlay_configmap(overlay_path)
    model_format = "onnx" if model_uri.lower().endswith(".onnx") else "pkl"
    update_configmap(configmap_path, model_uri, model_format, metadata_uri)

    ensure_git_identity()
    message = f"chore: promote model -> {model_uri}"
    subprocess.check_call(["git", "commit", "-m", message])

    actor = os.getenv("GIT_AUTHOR_NAME", "ci-bot")
    record_promotion(model_uri, overlay, reasons, actor)
    if policy["actions"].get("auto_promote", True):
        print("IMPROVED: promotion committed")
    else:
        print("IMPROVED: promotion committed (awaiting manual approval)")


if __name__ == "__main__":
    main()

