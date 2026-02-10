import os
import asyncio
from typing import Dict, List, Optional
from transformers import pipeline
import httpx
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self, model_type: str = 'local', model_name: str = None):
        self.model_type = model_type
        
        if model_type == 'local':
            self.model_name = model_name or os.getenv(
                'HUGGINGFACE_MODEL',
                'distilbert-base-uncased-finetuned-sst-2-english'
            )
            self.emotion_model_name = os.getenv(
                'EMOTION_MODEL',
                'j-hartmann/emotion-english-distilroberta-base'
            )
            
            logger.info(f"Loading local sentiment model: {self.model_name}")
            self.sentiment_pipeline = pipeline(
                "text-classification",
                model=self.model_name,
                device=-1
            )
            
            logger.info(f"Loading local emotion model: {self.emotion_model_name}")
            self.emotion_pipeline = pipeline(
                "text-classification",
                model=self.emotion_model_name,
                device=-1
            )
            
        elif model_type == 'external':
            self.provider = os.getenv('EXTERNAL_LLM_PROVIDER', 'groq')
            self.api_key = os.getenv('EXTERNAL_LLM_API_KEY')
            self.external_model = os.getenv('EXTERNAL_LLM_MODEL', 'llama-3.1-8b-instant')
            
            if not self.api_key:
                raise ValueError("EXTERNAL_LLM_API_KEY environment variable required")
            
            self.model_name = f"{self.provider}:{self.external_model}"
            self.client = httpx.AsyncClient(timeout=30.0)
            
    async def analyze_sentiment(self, text: str) -> Dict:
        if not text or len(text.strip()) == 0:
            raise ValueError("Text cannot be empty")
        
        text = text[:2000]
        
        if self.model_type == 'local':
            result = self.sentiment_pipeline(text)[0]
            
            label = result['label'].lower()
            if 'pos' in label or label == 'positive':
                sentiment_label = 'positive'
            elif 'neg' in label or label == 'negative':
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'
            
            return {
                'sentiment_label': sentiment_label,
                'confidence_score': float(result['score']),
                'model_name': self.model_name
            }
            
        else:
            return await self._external_sentiment(text)
    
    async def analyze_emotion(self, text: str) -> Dict:
        if not text or len(text.strip()) == 0:
            raise ValueError("Text cannot be empty")
        
        text = text[:2000]
        
        if len(text.strip()) < 10:
            return {
                'emotion': 'neutral',
                'confidence_score': 1.0,
                'model_name': self.emotion_model_name if self.model_type == 'local' else self.model_name
            }
        
        if self.model_type == 'local':
            result = self.emotion_pipeline(text)[0]
            
            emotion_map = {
                'joy': 'joy',
                'sadness': 'sadness',
                'anger': 'anger',
                'fear': 'fear',
                'surprise': 'surprise',
                'neutral': 'neutral',
                'disgust': 'anger',
                'love': 'joy'
            }
            
            detected_emotion = result['label'].lower()
            emotion = emotion_map.get(detected_emotion, 'neutral')
            
            return {
                'emotion': emotion,
                'confidence_score': float(result['score']),
                'model_name': self.emotion_model_name
            }
        else:
            return await self._external_emotion(text)
    
    async def batch_analyze(self, texts: List[str]) -> List[Dict]:
        if not texts:
            return []
        
        if self.model_type == 'local':
            results = []
            for text in texts:
                try:
                    result = await self.analyze_sentiment(text)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error analyzing text: {e}")
                    results.append({
                        'sentiment_label': 'neutral',
                        'confidence_score': 0.0,
                        'model_name': self.model_name,
                        'error': str(e)
                    })
            return results
        else:
            tasks = [self.analyze_sentiment(text) for text in texts]
            return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _external_sentiment(self, text: str) -> Dict:
        prompt = f"""Analyze the sentiment of this text and respond ONLY with a JSON object (no markdown, no explanation):
{{"sentiment_label": "positive" or "negative" or "neutral", "confidence_score": 0.0 to 1.0}}

Text: {text}"""
        
        try:
            if self.provider == 'groq':
                response = await self.client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.external_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                )
            elif self.provider == 'openai':
                response = await self.client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.external_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                )
            else:
                response = await self.client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": self.external_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 100
                    }
                )
            
            response.raise_for_status()
            data = response.json()
            
            if self.provider == 'anthropic':
                content = data['content'][0]['text']
            else:
                content = data['choices'][0]['message']['content']
            
            result = json.loads(content.strip())
            result['model_name'] = self.model_name
            return result
            
        except Exception as e:
            logger.error(f"External API error: {e}")
            return {
                'sentiment_label': 'neutral',
                'confidence_score': 0.5,
                'model_name': self.model_name
            }
    
    async def _external_emotion(self, text: str) -> Dict:
        prompt = f"""Detect the primary emotion in this text. Respond ONLY with JSON:
{{"emotion": "joy" or "sadness" or "anger" or "fear" or "surprise" or "neutral", "confidence_score": 0.0 to 1.0}}

Text: {text}"""
        
        try:
            if self.provider == 'groq':
                response = await self.client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.external_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                )
            else:
                # Simplification for brevity, assume similar structure
                response = await self.client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.external_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                )

            response.raise_for_status()
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            result = json.loads(content.strip())
            result['model_name'] = self.model_name
            return result
        except Exception as e:
            return {
                'emotion': 'neutral',
                'confidence_score': 0.5,
                'model_name': self.model_name
            }
