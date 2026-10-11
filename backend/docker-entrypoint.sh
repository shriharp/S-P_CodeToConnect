#!/bin/sh
set -eu

if [ ! -f /app/data/demo_news.jsonl ]; then
  cp -R /opt/kairos-seed-data/. /app/data/
fi

exec "$@"
