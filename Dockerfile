FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install production server
RUN pip install gunicorn

# Copy project
COPY . .

# Create staticfiles directory
RUN mkdir -p staticfiles logs

# Collect static files (run with proper env vars)
# RUN python manage.py collectstatic --noinput

EXPOSE 8000

# ✅ Use gunicorn instead of runserver
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "marketplace.wsgi:application"]