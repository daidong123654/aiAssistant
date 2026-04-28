#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="${WORK_DIR:-$HOME/Work}"

echo "This will recreate the n8n container while preserving the n8n_data volume."
echo "Work directory mounted into n8n: ${WORK_DIR} -> /work"
read -r -p "Continue? (y/N) " answer
case "$answer" in
  y|Y|yes|YES) ;;
  *) echo "Cancelled."; exit 0 ;;
esac

docker stop n8n >/dev/null 2>&1 || true
docker rm n8n >/dev/null 2>&1 || true

docker run -d \
  --name n8n \
  --restart unless-stopped \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -v "${WORK_DIR}:/work" \
  -e N8N_SECURE_COOKIE=false \
  -e N8N_HOST=localhost \
  -e N8N_PORT=5678 \
  n8nio/n8n

echo "n8n recreated. Open http://localhost:5678"
