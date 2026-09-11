#!/usr/bin/env sh
set -eu

mkdir -p \
  /app/system/jsondata \
  /app/system/output \
  /app/system/jsondata_aggregation \
  /app/system/output_aggregation \
  /app/system/.runtime \
  /app/vis/data \
  /app/vis/data_aggregation

python - <<'PY'
from vis_sync import sync_visualization_mode

for mode in ("global", "aggregation"):
    try:
        synced = sync_visualization_mode(mode)
        print(f"Initial visualization sync ({mode}): {', '.join(synced) if synced else 'no files'}", flush=True)
    except Exception as exc:
        print(f"Warning: initial visualization sync failed ({mode}): {exc}", flush=True)
PY

exec uvicorn api:app --host 0.0.0.0 --port "${PORT:-6001}"
