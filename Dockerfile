FROM python:3.11-slim

WORKDIR /app

# System dependencies (FAISS needs minimal deps with pip wheels)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure runtime directories exist
RUN mkdir -p app/uploads vector_store instance

EXPOSE 5000

# Production server — 2 workers safe for 1 GB RAM VM
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "--timeout", "120", "run:app"]
