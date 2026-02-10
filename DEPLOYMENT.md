# Deployment Guide

## Prerequisites
- Docker Engine 20.10+
- Docker Compose v2.0+
- Minimum 4GB RAM / 2 vCPUs
- 10GB Disk Space

## Production Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/Rushikesh-5706/real-time-sentiment-analysis-platform.git
   cd real-time-sentiment-analysis-platform
   ```

2. **Configure Environment**
   Copy `.env.example` to `.env` and update production values:
   ```bash
   cp .env.example .env
   ```
   **Critical Settings for Production:**
   - `POSTGRES_PASSWORD`: Set a strong, unique password.
   - `EXTERNAL_LLM_API_KEY`: Required if using external models (Groq/OpenAI).
   - `REDIS_PASSWORD`: (Optional) Enable password protection for Redis.

3. **Build and Deploy**
   ```bash
   docker-compose down --remove-orphans
   docker-compose up -d --build
   ```

4. **Verify Deployment**
   - Health Check: `curl http://localhost:8000/api/health`
   - Dashboard: Open `http://localhost:3000`

## Scaling Configuration

### Horizontal Scaling (Worker)
To handle higher ingestion rates (>1000 posts/min), scale the worker service:
```bash
docker-compose up -d --scale worker=3
```
*Note: Redis Consumer Groups automatically distribute load across worker instances.*

### Database Optimization
For high-volume deployments, consider:
- Increasing `postgres` shared memory in `docker-compose.yml`.
- Using an external managed PostgreSQL (RDS/Cloud SQL) by updating `DATABASE_URL`.

## Maintenance

**Backup Database:**
```bash
docker-compose exec postgres pg_dump -U sentiment_user sentiment_db > backup.sql
```

**View Logs:**
```bash
docker-compose logs -f --tail=100
```
