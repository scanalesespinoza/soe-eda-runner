import os
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse

import boto3
import joblib
import numpy as np
import onnxruntime as ort
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Inference Service")

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s","logger":"%(name)s"}'
)
handler.setFormatter(formatter)
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.INFO)
LOGGER = logging.getLogger("inference-service")

MODEL_SOURCE_PATH = os.getenv("MODEL_PATH", "/models/model.onnx")
MODEL_PATH = MODEL_SOURCE_PATH
MODEL_FORMAT = os.getenv("MODEL_FORMAT", "onnx")
MODEL_META_PATH = os.getenv("MODEL_META_PATH", "")
READY = False
ORT_SESSION = None
PKL_MODEL = None
SCALER = None
FEATURE_ORDER: List[str] = []


class PredictRequest(BaseModel):
    records: List[Dict[str, Any]]


class Health(BaseModel):
    status: str
    model_path: str
    model_format: str


def load_aux() -> None:
    global FEATURE_ORDER
    meta = os.getenv("FEATURES_JSON", MODEL_META_PATH)
    if meta and os.path.exists(meta):
        try:
            with open(meta) as f:
                data = json.load(f)
            FEATURE_ORDER[:] = data.get("feature_order", [])
        except Exception:
            FEATURE_ORDER = []


def to_matrix(records: List[Dict[str, Any]]) -> np.ndarray:
    if FEATURE_ORDER:
        return np.array(
            [[rec.get(key, 0) for key in FEATURE_ORDER] for rec in records],
            dtype=float,
        )
    keys = sorted({key for record in records for key in record.keys()})
    return np.array(
        [[rec.get(key, 0) for key in keys] for rec in records],
        dtype=float,
    )


def download_model_if_needed(source: str) -> str:
    if not source.startswith("s3://"):
        return source

    parsed = urlparse(source)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    if not bucket or not key:
        raise RuntimeError(f"Invalid S3 model path: {source}")

    target_dir = Path(os.getenv("MODEL_LOCAL_DIR", "/models"))
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(key).name or "model.onnx"
    local_path = target_dir / filename

    LOGGER.info(
        json.dumps(
            {
                "event": "MODEL_DOWNLOAD", 
                "source": source,
                "bucket": bucket,
                "key": key,
            }
        )
    )

    session = boto3.session.Session(
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        region_name=os.getenv("AWS_REGION", os.getenv("S3_REGION", "us-east-1")),
    )
    s3 = session.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT"),
    )

    try:
        s3.download_file(bucket, key, str(local_path))
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"Failed to download model from {source}") from exc

    return str(local_path)


def load_model() -> None:
    global READY, ORT_SESSION, PKL_MODEL
    resolved_path = download_model_if_needed(MODEL_SOURCE_PATH)
    globals()["MODEL_PATH"] = resolved_path
    if MODEL_FORMAT.lower() == "onnx":
        ORT_SESSION = ort.InferenceSession(
            resolved_path,
            providers=["CPUExecutionProvider"],
        )
    else:
        PKL_MODEL = joblib.load(resolved_path)
    load_aux()
    READY = True
    LOGGER.info(
        json.dumps(
            {
                "event": "MODEL_LOADED",
                "modelPath": resolved_path,
                "modelFormat": MODEL_FORMAT,
            }
        )
    )


@app.on_event("startup")
async def startup() -> None:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    load_model()
    LOGGER.info(
        json.dumps(
            {
                "event": "INFERENCE_READY",
                "modelPath": MODEL_PATH,
                "modelFormat": MODEL_FORMAT,
            }
        )
    )


@app.get("/healthz", response_model=Health)
def health() -> Health:
    status = "ready" if READY else "loading"
    return Health(status=status, model_path=MODEL_PATH, model_format=MODEL_FORMAT)


@app.post("/predict")
def predict(req: PredictRequest) -> Dict[str, Any]:
    if not READY:
        raise HTTPException(status_code=503, detail="Model not ready")
    X = to_matrix(req.records)
    if MODEL_FORMAT.lower() == "onnx":
        input_name = ORT_SESSION.get_inputs()[0].name
        y = ORT_SESSION.run(None, {input_name: X.astype(np.float32)})[0].tolist()
    else:
        y = PKL_MODEL.predict(X).tolist()
    result = {"predictions": y, "count": len(y)}
    LOGGER.info(
        json.dumps(
            {
                "event": "PREDICT_COMPLETED",
                "records": len(req.records),
                "modelPath": MODEL_PATH,
            }
        )
    )
    return result
