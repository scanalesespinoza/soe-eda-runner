#!/usr/bin/env bash
set -euo pipefail

: "${S3_ENDPOINT?}"
: "${S3_ACCESS_KEY?}"
: "${S3_SECRET_KEY?}"
: "${MODEL_PATH?}"

bucket=$(echo "$MODEL_PATH" | sed -E 's#s3://([^/]+)/.*#\1#')
key=$(echo "$MODEL_PATH" | sed -E 's#s3://[^/]+/(.*)#\1#')

aws --endpoint-url "$S3_ENDPOINT" s3 cp "s3://${bucket}/${key}" /models/model.onnx
