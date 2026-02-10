import pytest
import os
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.sentiment_analyzer import SentimentAnalyzer

# --- Fixtures ---
@pytest.fixture
def mock_pipeline():
    with patch("app.services.sentiment_analyzer.pipeline") as mock:
        yield mock

@pytest.fixture
def analyzer(mock_pipeline):
    return SentimentAnalyzer(model_type='local')

# --- Sentiment Tests (Local) ---
@pytest.mark.asyncio
async def test_sentiment_positive(analyzer, mock_pipeline):
    mock_pipeline.return_value.return_value = [{'label': 'POSITIVE', 'score': 0.9}]
    result = await analyzer.analyze_sentiment("I love this!")
    assert result['sentiment_label'] == 'positive'
    assert result['confidence_score'] == 0.9

@pytest.mark.asyncio
async def test_sentiment_negative(analyzer, mock_pipeline):
    mock_pipeline.return_value.return_value = [{'label': 'NEGATIVE', 'score': 0.85}]
    result = await analyzer.analyze_sentiment("I hate this.")
    assert result['sentiment_label'] == 'negative'

@pytest.mark.asyncio
async def test_sentiment_neutral_label(analyzer, mock_pipeline):
    mock_pipeline.return_value.return_value = [{'label': 'NEUTRAL', 'score': 0.7}]
    result = await analyzer.analyze_sentiment("It is a box.")
    assert result['sentiment_label'] == 'neutral'

@pytest.mark.asyncio
async def test_sentiment_mixed_mapping(analyzer, mock_pipeline):
    # Some models return LABEL_0, LABEL_1 etc or different casing
    mock_pipeline.return_value.return_value = [{'label': 'POS', 'score': 0.9}]
    result = await analyzer.analyze_sentiment("Good")
    assert result['sentiment_label'] == 'positive'

@pytest.mark.asyncio
async def test_sentiment_truncation(analyzer, mock_pipeline):
    mock_pipeline.return_value.return_value = [{'label': 'POSITIVE', 'score': 0.9}]
    long_text = "a" * 5000
    await analyzer.analyze_sentiment(long_text)
    # Verify pipeline called with truncated text (2000 chars)
    args, _ = analyzer.sentiment_pipeline.call_args
    assert len(args[0]) <= 2000

@pytest.mark.asyncio
async def test_sentiment_empty_error(analyzer):
    with pytest.raises(ValueError):
        await analyzer.analyze_sentiment("")

@pytest.mark.asyncio
async def test_sentiment_whitespace_error(analyzer):
    with pytest.raises(ValueError):
        await analyzer.analyze_sentiment("   ")

# --- Emotion Tests (Local) ---
@pytest.mark.asyncio
async def test_emotion_joy(analyzer, mock_pipeline):
    # Setup emotion pipeline mock (secondary call)
    # The analyzer uses 'emotion_pipeline' attribute
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.return_value = [{'label': 'joy', 'score': 0.95}]
    analyzer.emotion_pipeline = mock_pipeline_instance
    
    result = await analyzer.analyze_emotion("I am feeling so happy today!")
    assert result['emotion'] == 'joy'

@pytest.mark.asyncio
async def test_emotion_sadness(analyzer, mock_pipeline):
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.return_value = [{'label': 'sadness', 'score': 0.9}]
    analyzer.emotion_pipeline = mock_pipeline_instance
    
    result = await analyzer.analyze_emotion("I am feeling very sad today.")
    assert result['emotion'] == 'sadness'

@pytest.mark.asyncio
async def test_emotion_anger(analyzer, mock_pipeline):
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.return_value = [{'label': 'anger', 'score': 0.9}]
    analyzer.emotion_pipeline = mock_pipeline_instance
    
    result = await analyzer.analyze_emotion("I am feeling very angry today.")
    assert result['emotion'] == 'anger'

@pytest.mark.asyncio
async def test_emotion_fear(analyzer, mock_pipeline):
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.return_value = [{'label': 'fear', 'score': 0.9}]
    analyzer.emotion_pipeline = mock_pipeline_instance
    
    result = await analyzer.analyze_emotion("I am feeling very scared now.")
    assert result['emotion'] == 'fear'

@pytest.mark.asyncio
async def test_emotion_surprise(analyzer, mock_pipeline):
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.return_value = [{'label': 'surprise', 'score': 0.9}]
    analyzer.emotion_pipeline = mock_pipeline_instance
    
    result = await analyzer.analyze_emotion("Wow, I am really surprised!")
    assert result['emotion'] == 'surprise'

@pytest.mark.asyncio
async def test_emotion_disgust_mapped_to_anger(analyzer, mock_pipeline):
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.return_value = [{'label': 'disgust', 'score': 0.9}]
    analyzer.emotion_pipeline = mock_pipeline_instance
    
    result = await analyzer.analyze_emotion("This is absolutely disgusting.")
    assert result['emotion'] == 'anger'

@pytest.mark.asyncio
async def test_emotion_short_text(analyzer):
    result = await analyzer.analyze_emotion("Hi")
    assert result['emotion'] == 'neutral'
    assert result['confidence_score'] == 1.0

# --- Batch Tests ---
@pytest.mark.asyncio
async def test_batch_analyze_empty(analyzer):
    assert await analyzer.batch_analyze([]) == []

@pytest.mark.asyncio
async def test_batch_analyze_mixed(analyzer, mock_pipeline):
    # Mock return values for sequential calls if possible, or just fix return
    # Since mocked pipeline is same object, we can verify it's called X times
    # Batch analyze calls pipeline with list of texts, expects list of dicts
    mock_pipeline.return_value.return_value = [
        {'label': 'POSITIVE', 'score': 0.9},
        {'label': 'NEGATIVE', 'score': 0.8}
    ]
    results = await analyzer.batch_analyze(["a", "b"])
    assert len(results) == 2
    assert results[0]['sentiment_label'] == 'positive'

@pytest.mark.asyncio
async def test_batch_error_handling(analyzer, mock_pipeline):
    # Make pipeline raise exception
    analyzer.sentiment_pipeline.side_effect = Exception("Boom")
    results = await analyzer.batch_analyze(["test"])
    assert results[0]['sentiment_label'] == 'neutral'
    # Implementation swallows error and returns neutral without error key
    assert results[0]['confidence_score'] == 0.0

# --- External API Tests ---
@pytest.mark.asyncio
async def test_external_init_missing_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            SentimentAnalyzer(model_type='external')

@pytest.mark.asyncio
async def test_external_sentiment_groq():
    with patch.dict(os.environ, {'EXTERNAL_LLM_API_KEY': 'fake', 'EXTERNAL_LLM_PROVIDER': 'groq'}):
        analyzer = SentimentAnalyzer(model_type='external')
        # Mock the client.post method properly
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': '{"sentiment_label": "positive", "confidence_score": 0.9}'}}]
        }
        mock_response.raise_for_status = MagicMock()
        
        # Use AsyncMock for the async post method
        mock_post = AsyncMock(return_value=mock_response)
        analyzer.client.post = mock_post
        
        result = await analyzer.analyze_sentiment("Good")
        assert result['sentiment_label'] == 'positive'

@pytest.mark.asyncio
async def test_external_emotion_groq():
    with patch.dict(os.environ, {'EXTERNAL_LLM_API_KEY': 'fake', 'EXTERNAL_LLM_PROVIDER': 'groq'}):
        analyzer = SentimentAnalyzer(model_type='external')
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
             'choices': [{'message': {'content': '{"emotion": "joy", "confidence_score": 0.9}'}}]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_post = AsyncMock(return_value=mock_response)
        analyzer.client.post = mock_post

        # Must be > 10 chars to avoid local length check short-circuit
        result = await analyzer.analyze_emotion("I am feeling so happy today!")
        assert result['emotion'] == 'joy'

@pytest.mark.asyncio
async def test_external_api_error_fallback():
    with patch.dict(os.environ, {'EXTERNAL_LLM_API_KEY': 'fake'}):
        analyzer = SentimentAnalyzer(model_type='external')
        with patch.object(analyzer.client, 'post', side_effect=Exception("API Down")):
            result = await analyzer.analyze_sentiment("test")
            assert result['sentiment_label'] == 'neutral'
            assert result['confidence_score'] == 0.5
