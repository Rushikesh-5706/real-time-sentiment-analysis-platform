# System Architecture – Real-Time Sentiment Analysis Platform

## Architectural Overview
This platform follows a microservices-based architecture designed to simulate real-world, production-grade data pipelines. Each service is isolated, containerized, and communicates only through well-defined interfaces.

---

## Services and Responsibilities

### 1. PostgreSQL (Database)
- Stores raw social media posts
- Stores sentiment analysis results
- Stores alert and aggregation data
- Enforces schema, relationships, and indexes

### 2. Redis (Message Queue)
- Uses Redis Streams for message durability
- Enables producer–consumer decoupling
- Supports consumer groups and acknowledgments
- Acts as a lightweight cache for frequent queries

### 3. Ingester Service
- Generates realistic social media posts
- Publishes posts into Redis Streams
- Controls publishing rate
- Handles Redis connectivity failures gracefully

### 4. Worker Service
- Consumes messages from Redis Streams
- Performs sentiment and emotion analysis using AI models
- Persists results into PostgreSQL
- Acknowledges messages only after successful processing

### 5. Backend API Service
- Exposes REST APIs for historical data
- Provides aggregation and distribution endpoints
- Manages WebSocket connections for real-time updates
- Acts as the single interface for the frontend

### 6. Frontend Dashboard
- Built with React and Vite
- Displays sentiment distribution and trends
- Shows live feed of analyzed posts
- Connects to backend via REST and WebSocket

---

## Data Flow

1. Ingester generates a post
2. Post is published to Redis Stream
3. Worker consumes the message
4. Worker runs sentiment and emotion analysis
5. Results are saved to PostgreSQL
6. Backend APIs serve stored and aggregated data
7. WebSocket pushes live updates to frontend
8. Dashboard updates charts and live feed

---

## Database Design

### Tables
- **social_media_posts**
  - Stores raw posts and metadata
- **sentiment_analysis**
  - Stores model outputs and confidence scores
- **sentiment_alerts**
  - Stores triggered alert records

Indexes are applied on frequently queried columns such as timestamps, post identifiers, and sentiment labels.

---

## Design Decisions

### Why Redis Streams?
- Message persistence
- Consumer groups
- Reliable processing
- At-least-once delivery semantics

### Why FastAPI?
- Native async support
- Built-in WebSocket handling
- Automatic API validation

### Why Docker Compose?
- Zero-configuration startup
- Reproducible environments
- Easy evaluation and deployment

---

## Scalability Considerations
- Multiple worker replicas can be added for higher throughput
- Redis Streams support horizontal scaling
- Database can be upgraded to managed PostgreSQL
- Frontend can be served via CDN in production

---

## Security Considerations
- No hardcoded secrets
- Environment-based configuration
- Internal-only database and Redis exposure
- Clear separation of concerns across services

---

## Reliability and Fault Tolerance
- Health checks for core services
- Message reprocessing via Redis pending entries
- Graceful handling of temporary failures
- Durable storage with PostgreSQL volumes

---

## Conclusion
This architecture mirrors how real-world sentiment monitoring platforms are designed. The system emphasizes correctness, clarity, and maintainability while remaining simple enough for local execution and automated evaluation.
