FROM unclecode/crawl4ai:basic-arm64

WORKDIR /app

# Set Playwright to use a shared location
ENV PLAYWRIGHT_BROWSERS_PATH=/app/pw-browsers

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install browsers to the specific path defined above
RUN playwright install chromium --with-deps

COPY . .

# Create the user and ensure they own BOTH the app and the browser binaries
RUN useradd -m appuser && \
    chown -R appuser /app

USER appuser

EXPOSE 8000

# Tell the running app where the browsers are
ENV PLAYWRIGHT_BROWSERS_PATH=/app/pw-browsers

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
