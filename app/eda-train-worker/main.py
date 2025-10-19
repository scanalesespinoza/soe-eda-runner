from __future__ import annotations

import json
import os
import subprocess
import uuid

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="EDA Runner")


class EdaRequest(BaseModel):
    dataset_path: str
    output_path: str = "/out"
    outliers_col: str = "charges"


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
