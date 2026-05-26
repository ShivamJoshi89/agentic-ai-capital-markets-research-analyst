"""
Sentiment analysis for news articles
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class SentimentAnalysis:
    """
    Analyzes sentiment of news articles and text.
    """
    
    @staticmethod
    def classify_sentiment(text: str) -> Dict[str, float]:
        """
        Classify sentiment of text using keyword analysis.
        
        Args:
            text: Text to analyze
        
        Returns:
            Dict with positive, neutral, negative scores
        """
        if not text:
            return {
                "positive": 0.0,
                "neutral": 1.0,
                "negative": 0.0
            }
        
        text_lower = text.lower()
        
        positive_keywords = [
            "bullish", "surge", "rally", "jump", "soar", "gain", "beat",
            "profit", "growth", "strong", "rose", "outperform", "upgrade",
            "buy", "positive", "success", "record", "high", "recover",
            "excellent", "great", "amazing", "strong earnings"
        ]
        
        negative_keywords = [
            "bearish", "plunge", "crash", "fall", "decline", "loss", "miss",
            "weakness", "weak", "drop", "cut", "downgrade", "sell", "negative",
            "concern", "risk", "slump", "volatile", "down", "poor", "weak earnings"
        ]
        
        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)
        total = positive_count + negative_count
        
        if total == 0:
            return {
                "positive": 0.0,
                "neutral": 1.0,
                "negative": 0.0
            }
        
        positive_score = positive_count / total
        negative_score = negative_count / total
        neutral_score = 1.0 - positive_score - negative_score
        
        return {
            "positive": round(positive_score, 2),
            "neutral": round(neutral_score, 2),
            "negative": round(negative_score, 2)
        }