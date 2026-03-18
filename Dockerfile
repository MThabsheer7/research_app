FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (build-essential and libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements files explicitly
COPY requirements.txt requirements.txt

# Install all backend dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files (ignoring frontend in ideal cases, but copying is safe)
COPY . .

# Expose backend API port
EXPOSE 8001

# Run the app entrypoint (which configures proper asyncio event loops)
CMD ["python", "run.py"]
