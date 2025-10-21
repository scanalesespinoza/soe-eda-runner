from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="EDA Runner")


class EdaRequest(BaseModel):
    dataset_path: str
    output_path: str = "/out"
    outliers_col: str = "charges"


class RetrainRequest(BaseModel):
    dataset_path: str
    out_prefix: str = "/out"
    params: dict | None = None


@app.post("/eda/run")
def run_eda(req: EdaRequest):
    run_id = str(uuid.uuid4())[:8]
    outdir = os.path.join(req.output_path, run_id)
    os.makedirs(outdir, exist_ok=True)

    cmd = [
        "python",
        "/app/eda.py",
        "--input",
        req.dataset_path,
        "--output",
        outdir,
        "--outliers-col",
        req.outliers_col,
    ]

    process = subprocess.run(cmd, capture_output=True, text=True)
    status = "SUCCESS" if process.returncode == 0 else "FAILED"

    summary = {}
    if status == "SUCCESS":
        summary_path = os.path.join(outdir, "eda-summary.json")
        try:
            with open(summary_path, encoding="utf-8") as f:
                summary = json.load(f)
        except Exception:
            summary = {}

    return {
        "runId": run_id,
        "status": status,
        "stdout": process.stdout[-1000:],
        "stderr": process.stderr[-1000:],
        "summary": summary,
    }


@app.post("/train/retrain")
def retrain(req: RetrainRequest):
    run_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    outdir = os.path.join(req.out_prefix, "retrain", run_id)
    os.makedirs(outdir, exist_ok=True)

    train_cmd = [
        "python",
        "/app/train.py",
        "--dataset",
        req.dataset_path,
        "--outdir",
        outdir,
    ]
    if req.params:
        train_cmd.extend(["--params", json.dumps(req.params)])

    eval_cmd = [
        "python",
        "/app/evaluate.py",
        "--candidate",
        f"{outdir}/metrics.json",
        "--current",
        "/models/current/metrics.json",
        "--out",
        f"{outdir}/compare.json",
    ]

    train_proc = subprocess.run(train_cmd, capture_output=True, text=True)
    eval_proc = subprocess.run(eval_cmd, capture_output=True, text=True)

    improved = False
    compare_path = os.path.join(outdir, "compare.json")
    if os.path.exists(compare_path):
        try:
            with open(compare_path, encoding="utf-8") as f:
                compare = json.load(f)
            improved = bool(compare.get("improved", False))
        except Exception:
            improved = False

    status = "SUCCESS" if train_proc.returncode == 0 else "FAILED"
    return {
        "runId": run_id,
        "status": status,
        "improved": improved,
        "train": {
            "returncode": train_proc.returncode,
            "stdout": train_proc.stdout[-2000:],
            "stderr": train_proc.stderr[-2000:],
        },
        "evaluate": {
            "returncode": eval_proc.returncode,
            "stdout": eval_proc.stdout[-2000:],
            "stderr": eval_proc.stderr[-2000:],
        },
    }
