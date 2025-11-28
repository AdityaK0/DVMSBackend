#!/bin/bash
source env/bin/activate


echo "Starting Celery Worker..."
celery -A apps.core.celery.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --prefetch-multiplier=1
