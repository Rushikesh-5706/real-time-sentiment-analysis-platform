# Real-Time Sentiment Analysis Platform

A production-grade, microservices-based platform for analyzing sentiment and emotions in real-time social media streams. Built with modern technologies including FastAPI, Redis Streams, PostgreSQL, and React, this system processes thousands of posts per minute with AI-powered sentiment analysis.

## What This Platform Does

Imagine a system that continuously monitors social media conversations, instantly understanding whether people are happy, angry, or neutral about products and brands. That's exactly what this platform delivers:

- **Ingests** social media posts in real-time (60+ posts/minute)
- **Analyzes** sentiment (positive/negative/neutral) using state-of-the-art AI models
- **Detects** emotions (joy, anger, sadness, fear, surprise, neutral)
- **Stores** everything in a robust PostgreSQL database
- **Visualizes** insights through a beautiful, live-updating dashboard

## Key Features

- **Real-Time Processing** - Redis Streams ensure reliable, at-least-once message delivery
- **AI-Powered Analysis** - Local HuggingFace Transformers models (no API costs!)
- **Live Dashboard** - React-based UI with WebSocket updates
- **RESTful API** - Complete API for data access and aggregation
- **Fully Dockerized** - One command to start everything
- **Production Ready** - Comprehensive test suite with 45+ tests

## Architecture Overview

The platform consists of **6 microservices** working together:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Ingester   │────▶│    Redis    │────▶│   Worker    │
│  (Posts)    │     │  (Streams)  │     │ (AI Models) │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐            │
                    │  PostgreSQL │◀───────────┘
                    │  (Storage)  │
                    └──────┬──────┘
                           │
┌─────────────┐     ┌──────▼──────┐
│  Frontend   │◀────│   Backend   │
│  (React)    │     │  (FastAPI)  │
└─────────────┘     └─────────────┘
```

**Data Flow:**
1. **Ingester** generates realistic social media posts → Redis Streams
2. **Worker** consumes posts, runs AI analysis, saves to PostgreSQL
3. **Backend API** serves data via REST and WebSocket
4. **Frontend** displays live sentiment trends and analytics

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend API** | FastAPI (Python 3.9) | REST endpoints + WebSocket |
| **Worker** | Python + Transformers | Async AI processing |
| **Message Queue** | Redis 7 (Streams) | Reliable message delivery |
| **Database** | PostgreSQL 15 | Persistent storage |
| **Frontend** | React 18 + Vite | Live dashboard |
| **AI Models** | HuggingFace Transformers | Sentiment + Emotion analysis |
| **Deployment** | Docker + Docker Compose | Containerized services |

## Prerequisites

Before you begin, ensure you have:

- **Docker** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** v2+ (included with Docker Desktop)
- **4GB RAM** minimum (8GB recommended)
- **Ports 3000 and 8000** available

**Quick Check:**
```bash
docker --version          # Should show 20.10+
docker-compose --version  # Should show v2+
```

## Quick Start Guide

### Step 1: Clone the Repository

```bash
git clone https://github.com/Rushikesh-5706/real-time-sentiment-analysis-platform.git
cd real-time-sentiment-analysis-platform-main
```

### Step 2: Configure Environment (Optional)

The platform works out-of-the-box with default settings. For customization:

```bash
# Copy example environment file
cp .env.example .env

# Edit .env to customize (optional)
# - Database credentials
# - Redis configuration
# - AI model selection
# - External LLM API keys (optional)
```

### Step 3: Start All Services

```bash
# Start all 6 services in detached mode
docker-compose up -d

# This will:
# 1. Pull necessary Docker images
# 2. Build custom images for backend, worker, ingester, frontend
# 3. Start PostgreSQL and Redis
# 4. Initialize database schema
# 5. Start all application services
```

**First-time startup takes 2-3 minutes** (downloading AI models).

### Step 4: Verify Services are Running

```bash
# Check all services are healthy
docker-compose ps

# Expected output:
# NAME                  STATUS
# sentiment_backend     Up (healthy)
# sentiment_frontend    Up
# sentiment_ingester    Up
# sentiment_postgres    Up (healthy)
# sentiment_redis       Up (healthy)
# sentiment_worker      Up
```

### Step 5: Access the Platform

Once all services are running:

- **Frontend Dashboard**: http://localhost:3000
  - View live sentiment trends
  - See real-time post analysis
  - Monitor system statistics

- **Backend API**: http://localhost:8000
  - API Documentation: http://localhost:8000/docs
  - Health Check: http://localhost:8000/api/health

### Step 6: Verify Data is Flowing

```bash
# Check health endpoint
curl http://localhost:8000/api/health | python3 -m json.tool

# Expected output:
# {
#     "status": "healthy",
#     "services": {
#         "database": "connected",
#         "redis": "connected"
#     },
#     "stats": {
#         "total_posts": 150,      # Growing number
#         "total_analyses": 150,
#         "recent_posts_1h": 150
#     }
# }
```

```bash
# View recent analyzed posts
curl "http://localhost:8000/api/posts?limit=5" | python3 -m json.tool

# You should see realistic posts like:
# "I absolutely love PlayStation 5!" → positive (99.98%), joy
# "Terrible experience with Amazon Prime" → negative (98.45%), anger
```

## API Reference

### Health Check
```bash
GET /api/health
```
Returns system status and statistics.

### Get Posts
```bash
GET /api/posts?limit=10&offset=0
```
Retrieve paginated list of analyzed posts with sentiment scores.

### Sentiment Aggregation
```bash
GET /api/sentiment/aggregate?hours=24
```
Get time-series sentiment data for the last N hours.

### Sentiment Distribution
```bash
GET /api/sentiment/distribution
```
Get overall sentiment breakdown (positive/negative/neutral percentages).

### WebSocket (Real-Time Updates)
```javascript
ws://localhost:8000/ws/sentiment
```
Connect to receive live sentiment updates as posts are analyzed.

**Full API documentation**: http://localhost:8000/docs (Swagger UI)

## Running Tests

The platform includes a comprehensive test suite with 45+ tests covering unit, integration, and performance scenarios.

```bash
# Run all tests
docker-compose exec backend pytest tests/ -v

# Run with coverage report
docker-compose exec backend pytest tests/ --cov=app --cov-report=term

# Run specific test file
docker-compose exec backend pytest tests/test_sentiment.py -v

# Run integration tests only
docker-compose exec backend pytest tests/test_integration.py -v
```

**Expected output:**
```
===================== 45 passed in 12.34s =====================
```

## Project Structure

```
real-time-sentiment-analysis-platform-main/
│
├── docker-compose.yml          # Orchestrates all 6 services
├── .env.example                # Environment configuration template
├── README.md                   # This file
├── ARCHITECTURE.md             # Detailed system design
├── API_DOCUMENTATION.md        # Complete API reference
├── DEPLOYMENT.md               # Production deployment guide
│
├── backend/                    # FastAPI backend service
│   ├── app/
│   │   ├── api/               # REST endpoints
│   │   ├── models/            # SQLAlchemy models
│   │   └── main.py            # FastAPI application
│   ├── services/              # Business logic
│   │   ├── sentiment_analyzer.py
│   │   └── alerting.py
│   ├── tests/                 # Test suite (45+ tests)
│   ├── Dockerfile
│   └── requirements.txt
│
├── worker/                     # AI processing worker
│   ├── worker.py              # Async message consumer
│   ├── Dockerfile
│   └── requirements.txt
│
├── ingester/                   # Data ingestion service
│   ├── ingester.py            # Post generator
│   ├── Dockerfile
│   └── requirements.txt
│
└── frontend/                   # React dashboard
    ├── src/
    ├── Dockerfile
    ├── package.json
    └── vite.config.js
```

## Useful Commands

### Managing Services

```bash
# Stop all services
docker-compose down

# Restart specific service
docker-compose restart backend

# Rebuild and restart (after code changes)
docker-compose up -d --build

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f worker
```

### Database Operations

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U sentiment_user -d sentiment_db

# View posts count
docker-compose exec postgres psql -U sentiment_user -d sentiment_db -c "SELECT COUNT(*) FROM social_media_posts;"

# View recent analyses
docker-compose exec postgres psql -U sentiment_user -d sentiment_db -c "SELECT post_id, sentiment_label, confidence_score FROM sentiment_analysis ORDER BY analyzed_at DESC LIMIT 10;"
```

### Redis Operations

```bash
# Check Redis stream length
docker-compose exec redis redis-cli XLEN social_posts_stream

# View consumer groups
docker-compose exec redis redis-cli XINFO GROUPS social_posts_stream

# Monitor Redis commands in real-time
docker-compose exec redis redis-cli MONITOR
```

## Troubleshooting

### Services Won't Start

**Problem:** `docker-compose up -d` fails or services crash immediately.

**Solutions:**
```bash
# 1. Check Docker resources (need 4GB+ RAM)
docker info | grep Memory

# 2. Clean up and restart
docker-compose down -v  # Remove volumes
docker-compose up -d --build

# 3. Check logs for specific errors
docker-compose logs backend
docker-compose logs worker
```

### No Data Appearing in Dashboard

**Problem:** Dashboard shows 0 posts or no updates.

**Solutions:**
```bash
# 1. Verify ingester is running
docker-compose logs ingester | tail -20

# 2. Check worker is processing
docker-compose logs worker | tail -20

# 3. Verify database has data
curl http://localhost:8000/api/health
```

### Port Already in Use

**Problem:** Error: "port 3000 (or 8000) is already allocated"

**Solutions:**
```bash
# Find what's using the port
lsof -i :3000  # or :8000

# Kill the process or change ports in docker-compose.yml
# Edit docker-compose.yml:
# ports:
#   - "3001:3000"  # Change host port
```

### Worker Not Processing Messages

**Problem:** Posts in database but no sentiment analysis.

**Solutions:**
```bash
# 1. Check worker logs for errors
docker-compose logs worker | grep ERROR

# 2. Verify AI models loaded successfully
docker-compose logs worker | grep "Loading local"

# 3. Restart worker
docker-compose restart worker
```

## Performance Metrics

Based on testing with Docker Desktop (4 CPU cores, 8GB RAM):

| Metric | Value |
|--------|-------|
| **Ingestion Rate** | 60 posts/minute |
| **Processing Throughput** | 8.5 messages/second |
| **API Response Time (p95)** | <200ms |
| **WebSocket Latency** | <50ms |
| **Database Capacity** | 10,000+ posts tested |
| **Memory Usage** | Backend: 180MB, Worker: 850MB |

## Additional Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed system design, data flow, and component interactions
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference with examples
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide

## Contributing

This project was built for educational purposes. If you'd like to extend it:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is intended for educational and evaluation purposes.

## Acknowledgments

- **HuggingFace** for providing excellent pre-trained models
- **FastAPI** for the amazing Python web framework
- **Redis** for reliable message streaming
- **PostgreSQL** for robust data storage

---

