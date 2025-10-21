FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 libpng16-16 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

COPY ml/pipelines/eda.py /app/eda.py
COPY ml/pipelines/train.py /app/train.py
COPY ml/pipelines/evaluate.py /app/evaluate.py
COPY ml/pipelines/package.py /app/package.py
COPY app/eda-train-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/eda-train-worker/ /app/

ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
