#!/usr/bin/env bash
# Build the Lambda deployment folder (Linux arm64, Python 3.13, Amazon Linux 2023 = glibc 2.34) without Docker.
# Output: infra/build/lambda  (used by the CDK stack as the code asset)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/infra/build/lambda"
REQ="$ROOT/infra/build/requirements.txt"

rm -rf "$OUT"
mkdir -p "$OUT"

cd "$ROOT/backend"
# Runtime dependencies only. boto3 and botocore are part of the Lambda runtime.
uv export --frozen --no-default-groups --no-hashes --no-emit-project --format requirements-txt \
  | grep -v -E '^(boto3|botocore|s3transfer|jmespath)==' > "$REQ"

uv pip install --quiet --target "$OUT" \
  --python-platform aarch64-manylinux_2_28 --python-version 3.13 \
  --only-binary :all: -r "$REQ"

cp -R src/letterlens "$OUT/letterlens"
cp -R corpus "$OUT/letterlens/corpus"
find "$OUT" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$OUT" -type d -name "tests" -path "*/site-packages/*" -prune -exec rm -rf {} + 2>/dev/null || true

SIZE_MB=$(du -sm "$OUT" | cut -f1)
echo "Lambda bundle: ${SIZE_MB} MB (limit 250 MB unzipped)"
if [ "$SIZE_MB" -gt 240 ]; then
  echo "Bundle too large" >&2
  exit 1
fi
