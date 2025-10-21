from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import json
import joblib
import onnxruntime as ort
import numpy as np
from typing import List, Dict, Any

app = FastAPI(title="Inference Service")

MODEL_PATH = os.getenv("MODEL_PATH", "/models/model.onnx")
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


def load_model() -> None:
    global READY, ORT_SESSION, PKL_MODEL
    if MODEL_FORMAT.lower() == "onnx":
        ORT_SESSION = ort.InferenceSession(
            MODEL_PATH,
            providers=["CPUExecutionProvider"],
        )
    else:
        PKL_MODEL = joblib.load(MODEL_PATH)
    load_aux()
    READY = True


@app.on_event("startup")
def startup() -> None:
    if not os.path.exists(MODEL_PATH):
        pass
    load_model()


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
    return {"predictions": y, "count": len(y)}
