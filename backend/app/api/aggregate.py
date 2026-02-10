from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

router = APIRouter()

@router.get("/sentiment/aggregate")
async def get_sentiment_aggregate(
    period: str = Query("hour", regex="^(minute|hour|day)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(hours=24)
    
    if period == "minute":
        trunc_func = "date_trunc('minute', analyzed_at)"
    elif period == "hour":
        trunc_func = "date_trunc('hour', analyzed_at)"
    else:  # day
        trunc_func = "date_trunc('day', analyzed_at)"
    
    async with AsyncSessionLocal() as session:
        query = f"""
        SELECT 
            {trunc_func} as timestamp,
            sentiment_label,
            COUNT(*) as count,
            AVG(confidence_score) as avg_confidence
        FROM sentiment_analysis
        WHERE analyzed_at >= :start_date AND analyzed_at <= :end_date
        GROUP BY timestamp, sentiment_label
        ORDER BY timestamp ASC
        """
        
        rows = (await session.execute(
            text(query),
            {'start_date': start_date, 'end_date': end_date}
        )).all()
    
    data_dict = {}
    for row in rows:
        ts = row.timestamp.isoformat()
        if ts not in data_dict:
            data_dict[ts] = {
                'timestamp': ts,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'total_count': 0,
                'average_confidence': []
            }
        
        label = row.sentiment_label
        count = row.count
        
        if label == 'positive':
            data_dict[ts]['positive_count'] = count
        elif label == 'negative':
            data_dict[ts]['negative_count'] = count
        elif label == 'neutral':
            data_dict[ts]['neutral_count'] = count
            
        data_dict[ts]['total_count'] += count
        if row.avg_confidence:
            data_dict[ts]['average_confidence'].append(row.avg_confidence)
    
    final_data = []
    total_positive = 0
    total_negative = 0
    total_neutral = 0
    
    sorted_ts = sorted(data_dict.keys())
    
    for ts in sorted_ts:
        d = data_dict[ts]
        total = d['total_count']
        
        d['positive_percentage'] = (d['positive_count'] / total * 100) if total else 0.0
        d['negative_percentage'] = (d['negative_count'] / total * 100) if total else 0.0
        d['neutral_percentage'] = (d['neutral_count'] / total * 100) if total else 0.0
        
        if d['average_confidence']:
            d['average_confidence'] = sum(d['average_confidence']) / len(d['average_confidence'])
        else:
            d['average_confidence'] = 0.0
            
        total_positive += d['positive_count']
        total_negative += d['negative_count']
        total_neutral += d['neutral_count']
        
        final_data.append(d)
        
    # CRITICAL: Ensure at least one time period is returned even if no data
    if not final_data:
        # Generate a single time period with zero counts
        if period == 'minute':
            base_time = end_date.replace(second=0, microsecond=0)
        elif period == 'hour':
            base_time = end_date.replace(minute=0, second=0, microsecond=0)
        else:  # day
            base_time = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        final_data = [{
            'timestamp': base_time.isoformat(),
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'total_count': 0,
            'positive_percentage': 0.0,
            'negative_percentage': 0.0,
            'neutral_percentage': 0.0,
            'average_confidence': 0.0
        }]
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "data": final_data,
        "summary": {
            "total_posts": total_positive + total_negative + total_neutral,
            "positive_total": total_positive,
            "negative_total": total_negative,
            "neutral_total": total_neutral
        }
    }
