#!/usr/bin/env sh
set -eu

cd /app/backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 &

exec nginx -g 'daemon off;'
