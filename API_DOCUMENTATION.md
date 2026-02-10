# API Documentation

## Base URL
`http://localhost:8000/api`

## Health Check
**GET** `/health`
Returns the operational status of all system components.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "redis": "connected"
  },
  "stats": {
    "total_posts": 15430,
    "total_analyses": 15430,
    "recent_posts_1h": 1200
  }
}
```

## Posts
**GET** `/posts`
Retrieve paginated list of analyzed posts with filtering options.

**Parameters:**
- `limit` (int, default: 50): Number of posts to return.
- `offset` (int, default: 0): Pagination offset.
- `source` (string, optional): Filter by source (e.g., "twitter", "reddit").
- `sentiment` (string, optional): Filter by sentiment ("positive", "negative", "neutral").
- `start_date` (ISO8601, optional): Filter posts created after this date.
- `end_date` (ISO8601, optional): Filter posts created before this date.

**Response:**
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "posts": [
    {
      "post_id": "12345",
      "content": "This new feature is amazing!",
      "source": "twitter",
      "sentiment": {
        "label": "positive",
        "confidence": 0.98,
        "emotion": "joy"
      }
    }
  ]
}
```

## Analytics
**GET** `/sentiment/aggregate`
Get aggregated sentiment metrics over time.

**Parameters:**
- `period` (string): "minute", "hour", or "day".
- `start_date` (ISO8601, optional).
- `end_date` (ISO8601, optional).

**Response:**
```json
{
  "period": "hour",
  "data": [
    {
      "timestamp": "2023-10-27T10:00:00",
      "positive_count": 45,
      "negative_count": 12,
      "neutral_count": 20,
      "average_confidence": 0.85
    }
  ]
}
```

## Alerts & Metrics
**GET** `/alerts`
Retrieve recent sentiment alerts.

**GET** `/metrics`
System-wide metrics for monitoring.

## WebSocket
**WS** `/ws/sentiment`
Real-time stream of analyzed posts.

**Message Format:**
```json
{
  "type": "new_post",
  "data": {
    "post_id": "...",
    "content": "...",
    "sentiment_label": "positive",
    "emotion": "joy"
  }
}
```
