#!/usr/bin/env bash

set -euo pipefail
cd /home/username/projects/tempest

mkdir -p logs
LOG="logs/sync_$(date +%F).log"

{
  echo "=== Tempest sync start $(date -u '+%F %T UTC') ==="
  set -a && source ./.env && set +a

  python ./src/sync_weather.py \
    --api_token "$TEMPEST_API_TOKEN" \
    --database ./data/bronze/weather.db \
    --device_id "${TEMPEST_DEVICE_IDS:-$TEMPEST_DEVICE_ID}" \
    -v

  echo "=== Tempest sync done  $(date -u '+%F %T UTC') ==="
} >> "$LOG" 2>&1

