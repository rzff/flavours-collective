# ============================
# Adaptive-Scraper Dockerfile
# ============================

# Use a lightweight Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Metadata
LABEL maintainer="you@example.com"
LABEL project="Adaptive-Scraper"
LABEL description="Adaptive-Scraper: An async FastAPI web scraping service with Playwright support"

# Install system dependencies for Playwright and other tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxcomposite1 \
    libxrandr2 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install Playwright browser binaries
RUN playwright install --with-deps chromium

# Copy application files
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start the Adaptive-Scraper app
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
