#!/bin/sh
set -e

python - <<'PY'
import os
import time

import psycopg

engine = (os.getenv('DB_ENGINE', 'postgres') or 'postgres').lower()
if engine == 'sqlite':
    raise SystemExit(0)

host = os.getenv('POSTGRES_HOST', 'postgres')
port = int(os.getenv('POSTGRES_PORT', '5432'))
user = os.getenv('POSTGRES_USER', 'opticart_user')
password = os.getenv('POSTGRES_PASSWORD', 'opticart_password')
dbname = os.getenv('POSTGRES_DB', 'opticart_db')

dsn = f"host={host} port={port} user={user} password={password} dbname={dbname}"

for attempt in range(30):
    try:
        with psycopg.connect(dsn):
            break
    except Exception:
        if attempt == 29:
            raise
        time.sleep(1)
PY

python manage.py migrate --noinput

if [ -f /app/product_images.txt ]; then
    python manage.py update_product_images --file /app/product_images.txt || true
fi

exec python manage.py runserver 0.0.0.0:8000
