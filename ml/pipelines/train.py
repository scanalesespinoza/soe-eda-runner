"""Training pipeline for the SOE-EDA runner models.

This script is intentionally opinionated so it can be invoked from a variety of
contexts (local development, the training worker container, CI, etc.).  The
main responsibilities are:

* Load a tabular dataset (CSV expected) identified by ``--dataset``.
* Train a simple regression model (default: ``LinearRegression``) using a
  one-hot encoded representation for categorical variables.
* Persist the trained model in ONNX format when the conversion succeeds (falls
  back to a ``.pkl`` artefact otherwise).
* Emit accompanying artefacts: ``metrics.json``, ``model-card.yaml`` and a
  compact metadata JSON with the feature order so that the inference service
  can reproduce the same input contract.

The command line interface is designed to be backwards compatible with the
worker from previous iterations and supports passing a JSON blob of model
parameters through ``--params``.  Additional algorithms could be plugged in in
the future, but keeping the implementation lean helps keeping the example
manageable.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


DEFAULT_TARGET = "charges"


@dataclass
class TrainConfig:
    dataset: Path
    outdir: Path
    target: str = DEFAULT_TARGET
    params: Dict[str, Any] | None = None
    test_size: float = 0.2
    random_state: int = 42


def parse_args() -> TrainConfig:
    parser = argparse.ArgumentParser(description="Train regression model")
    parser.add_argument("--dataset", required=True, help="Path to the dataset (CSV)")
    parser.add_argument("--outdir", required=True, help="Directory to place outputs")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="Target column name")
    parser.add_argument("--params", help="JSON encoded hyper-parameters", default=None)
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of the dataset reserved for evaluation",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed used for data splitting",
    )

    args = parser.parse_args()
    params: Dict[str, Any] | None = None
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise SystemExit(f"Invalid JSON provided to --params: {exc}") from exc

    return TrainConfig(
        dataset=Path(args.dataset),
        outdir=Path(args.outdir),
        target=args.target,
        params=params,
        test_size=args.test_size,
        random_state=args.random_state,
    )


def load_dataset(config: TrainConfig) -> Tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(config.dataset)
    if config.target not in df.columns:
        raise SystemExit(f"Target column '{config.target}' not present in dataset")
    y = df[config.target]
    X = df.drop(columns=[config.target])
    return X, y


def prepare_features(X: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Encode categorical columns using one-hot encoding.

    Returns the transformed dataframe and metadata describing the
    transformation.  The inference service relies on ``feature_order`` when it
    converts incoming payloads to matrices, therefore we persist that in a
    machine readable companion file.
    """

    categorical = X.select_dtypes(exclude=[np.number]).columns.tolist()
    transformed = pd.get_dummies(X, columns=categorical, drop_first=False)
    transformed = transformed.astype(float)
    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "categorical_columns": categorical,
        "feature_order": transformed.columns.tolist(),
    }
    return transformed, metadata


def build_model(params: Dict[str, Any] | None) -> LinearRegression:
    supported = {"fit_intercept", "copy_X", "positive"}
    kwargs = {k: v for k, v in (params or {}).items() if k in supported}
    model = LinearRegression(**kwargs)
    return model


def export_model(
    model: LinearRegression,
    feature_order: list[str],
    outdir: Path,
) -> Tuple[Path, str]:
    """Persist the model and return the artefact path plus its format."""

    onnx_path = outdir / "model.onnx"
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType

        initial_type = [("input", FloatTensorType([None, len(feature_order)]))]
        onnx_model = convert_sklearn(model, initial_types=initial_type)
        with open(onnx_path, "wb") as f:
            f.write(onnx_model.SerializeToString())
        return onnx_path, "onnx"
    except Exception as exc:  # pragma: no cover - depends on optional deps
        fallback_path = outdir / "model.pkl"
        print(f"[train] Failed to export ONNX ({exc}); storing pickle at {fallback_path}")
        joblib.dump(model, fallback_path)
        return fallback_path, "pkl"


def compute_metrics(
    model: LinearRegression,
    X_test: np.ndarray,
    y_test: pd.Series,
) -> Dict[str, float]:
    preds = model.predict(X_test)
    rmse = math.sqrt(mean_squared_error(y_test, preds))
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    return {"rmse": float(rmse), "mae": float(mae), "r2": float(r2)}


def write_json(path: Path, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def write_model_card(
    path: Path,
    dataset: Path,
    target: str,
    params: Dict[str, Any] | None,
    metrics: Dict[str, float],
    metadata: Dict[str, Any],
    model_format: str,
    train_rows: int,
    test_rows: int,
) -> None:
    card = {
        "model": {
            "type": "linear_regression",
            "format": model_format,
            "created_at": datetime.utcnow().isoformat() + "Z",
        },
        "dataset": {
            "path": str(dataset),
            "target": target,
            "train_rows": int(train_rows),
            "test_rows": int(test_rows),
        },
        "training": {
            "parameters": params or {},
        },
        "features": {
            "count": len(metadata["feature_order"]),
            "categorical": metadata["categorical_columns"],
            "feature_order": metadata["feature_order"],
        },
        "metrics": metrics,
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(card, f, sort_keys=False)


def main() -> None:
    config = parse_args()
    config.outdir.mkdir(parents=True, exist_ok=True)

    X_raw, y = load_dataset(config)
    X, metadata = prepare_features(X_raw)

    X_train, X_test, y_train, y_test = train_test_split(
        X.values,
        y.values,
        test_size=config.test_size,
        random_state=config.random_state,
    )

    model = build_model(config.params)
    model.fit(X_train, y_train)

    metrics = compute_metrics(model, X_test, y_test)

    model_path, model_format = export_model(model, metadata["feature_order"], config.outdir)

    metrics_path = config.outdir / "metrics.json"
    write_json(metrics_path, metrics)

    metadata_path = config.outdir / "model-metadata.json"
    metadata_to_store = {
        **metadata,
        "target": config.target,
        "model_format": model_format,
    }
    write_json(metadata_path, metadata_to_store)

    model_card_path = config.outdir / "model-card.yaml"
    write_model_card(
        model_card_path,
        config.dataset,
        config.target,
        config.params,
        metrics,
        metadata,
        model_format,
        train_rows=len(X_train),
        test_rows=len(X_test),
    )

    print(f"[train] Model artefact: {model_path}")
    print(f"[train] Metrics written to: {metrics_path}")
    print(f"[train] Model card: {model_card_path}")
    print(f"[train] Metadata: {metadata_path}")


if __name__ == "__main__":
    main()

