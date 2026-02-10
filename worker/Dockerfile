FROM python:3.9-slim

WORKDIR /app

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend services for sentiment analyzer
COPY backend/services /app/backend/services
COPY backend/requirements.txt /app/backend/

# Install dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
RUN pip install --no-cache-dir redis sqlalchemy[asyncio] asyncpg

COPY worker/worker.py .

CMD ["python", "-u", "worker.py"]
