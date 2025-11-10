# --------------------------------------------------
# 🐍 Base Image
# --------------------------------------------------
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Prevent .pyc files & enable stdout flushing
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# --------------------------------------------------
# 🧰 System Dependencies
# --------------------------------------------------
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# 📦 Install Python Dependencies
# --------------------------------------------------
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------
# ⚙️ Gunicorn (for production server)
# --------------------------------------------------
RUN pip install gunicorn

# --------------------------------------------------
# 🧱 Copy Project
# --------------------------------------------------
COPY . .

# --------------------------------------------------
# 🗂️ Prepare runtime directories
# --------------------------------------------------
RUN mkdir -p staticfiles logs media

# --------------------------------------------------
# ⚡ Health check script (optional, future use)
# --------------------------------------------------
HEALTHCHECK CMD curl --fail http://localhost:8000/health/ || exit 1

# --------------------------------------------------
# 🚀 Default Command (Gunicorn)
# --------------------------------------------------
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "marketplace.wsgi:application"]
