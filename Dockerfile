FROM python:3.12.8-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/
COPY migrations/ migrations/
COPY scripts/wait_for_db.py scripts/wait_for_db.py

ENV PORT=8080
EXPOSE 8080

# Use the wait script to block until DB is reachable, then exec uvicorn
CMD ["python", "scripts/wait_for_db.py", "uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
