#!/usr/bin/env sh
set -eu

mkdir -p \
  /app/system/jsondata \
  /app/system/output \
  /app/system/jsondata_aggregation \
  /app/system/output_aggregation \
  /app/system/jsondata_global_plus \
  /app/system/output_global_plus \
  /app/system/.runtime \
  /app/vis/data \
  /app/vis/data_aggregation \
  /app/vis/data_global_plus

python - <<'PY'
from generate_global_plus import build_global_plus_jsondata
from vis_sync import sync_visualization_mode

try:
    generated = build_global_plus_jsondata()
    print(f"Generated global_plus jsondata: {', '.join(generated)}", flush=True)
except Exception as exc:
    print(f"Warning: global_plus jsondata generation failed: {exc}", flush=True)

for mode in ("global", "global_plus", "aggregation"):
    try:
        synced = sync_visualization_mode(mode)
        print(f"Initial visualization sync ({mode}): {', '.join(synced) if synced else 'no files'}", flush=True)
    except Exception as exc:
        print(f"Warning: initial visualization sync failed ({mode}): {exc}", flush=True)
PY

exec uvicorn api:app --host 0.0.0.0 --port "${PORT:-6001}"
