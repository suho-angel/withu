#!/usr/bin/env sh
set -e

echo "[entrypoint] Waiting for MySQL..."
# Simple wait loop
RETRIES=30
until nc -z "$MYSQL_HOST" "$MYSQL_PORT" || [ $RETRIES -eq 0 ]; do
  echo "Waiting for MySQL ($MYSQL_HOST:$MYSQL_PORT), $RETRIES retries left..."
  RETRIES=$((RETRIES-1))
  sleep 2
done

if [ $RETRIES -eq 0 ]; then
  echo "MySQL 연결 실패" >&2
  exit 1
fi

echo "[entrypoint] Migrations skipped (toy mode). Tables will auto-create if missing."

echo "[entrypoint] Starting app..."
echo "[entrypoint] Starting gunicorn..."
exec gunicorn -b 0.0.0.0:5000 -w "${GUNICORN_WORKERS:-3}" --threads "${GUNICORN_THREADS:-2}" --timeout "${GUNICORN_TIMEOUT:-60}" wsgi:app
