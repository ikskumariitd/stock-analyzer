# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download TextBlob corpora (needed for sentiment analysis)
RUN python -m textblob.download_corpora

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Expose port (Cloud Run uses PORT env variable)
EXPOSE 8080

# Run the application
# Cloud Run sets PORT environment variable, default to 8080
# Set WORKDIR to backend so imports like 'from sp100_tickers' work
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
