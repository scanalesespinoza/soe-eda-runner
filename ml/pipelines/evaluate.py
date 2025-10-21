"""Utility script used to compare a candidate model against the current one.

The evaluation logic mirrors the policy stored under
``ml/policies/promotion.yaml``.  When the policy file is not available we fall
back to sensible defaults, matching the thresholds documented in the
instructions for this iteration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Tuple

import yaml


DEFAULT_THRESHOLDS = {"r2_min_gain": 0.01, "rmse_min_drop": 100}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare model metrics")
    parser.add_argument("--candidate", required=True, help="Path to candidate metrics.json")
    parser.add_argument("--current", required=True, help="Path to current metrics.json")
    parser.add_argument("--out", required=True, help="Destination for the comparison JSON")
    return parser.parse_args()


def load_json(path: str) -> Dict[str, float]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def load_thresholds() -> Dict[str, float]:
    policy_path = Path("ml/policies/promotion.yaml")
    if policy_path.exists():
        with open(policy_path, encoding="utf-8") as f:
            policy = yaml.safe_load(f) or {}
        thresholds = policy.get("thresholds", {})
        merged = DEFAULT_THRESHOLDS.copy()
        merged.update({k: float(v) for k, v in thresholds.items() if isinstance(v, (int, float))})
        return merged
    return DEFAULT_THRESHOLDS


def compute_deltas(
    current: Dict[str, float],
    candidate: Dict[str, float],
) -> Tuple[float, float, float]:
    candidate_r2 = float(candidate.get("r2", 0.0))
    current_r2 = float(current.get("r2", 0.0))
    candidate_rmse = float(candidate.get("rmse", float("inf")))
    current_rmse = float(current.get("rmse", float("inf")))
    r2_gain = candidate_r2 - current_r2
    rmse_delta = candidate_rmse - current_rmse
    rmse_drop = current_rmse - candidate_rmse
    return r2_gain, rmse_delta, rmse_drop


def evaluate(current: Dict[str, float], candidate: Dict[str, float]) -> Dict[str, object]:
    thresholds = load_thresholds()
    if not candidate:
        return {
            "current": current,
            "candidate": candidate,
            "improved": False,
            "reasons": ["candidate metrics unavailable"],
            "thresholds": thresholds,
        }

    if not current:
        return {
            "current": current,
            "candidate": candidate,
            "improved": True,
            "reasons": ["no current model"],
            "thresholds": thresholds,
        }

    r2_gain, rmse_delta, rmse_drop = compute_deltas(current, candidate)
    improved = (
        r2_gain >= thresholds["r2_min_gain"]
        and rmse_drop >= thresholds["rmse_min_drop"]
    )

    reasons = [
        f"r2 {r2_gain:+.4f}",
        f"rmse {rmse_delta:+.4f}",
    ]

    return {
        "current": current,
        "candidate": candidate,
        "improved": improved,
        "reasons": reasons,
        "thresholds": thresholds,
    }


def main() -> None:
    args = parse_args()
    current = load_json(args.current)
    candidate = load_json(args.candidate)
    result = evaluate(current, candidate)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    status = "IMPROVED" if result["improved"] else "NOT IMPROVED"
    print(f"[evaluate] Comparison stored in {args.out} — {status}")


if __name__ == "__main__":
    main()

