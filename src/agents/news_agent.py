"""
News Agent
Collects and analyzes recent company news and sentiment.
"""

import logging
from typing import Dict, Any
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_sources.news_client import NewsClient
from analytics.sentiment_analysis import SentimentAnalysis

logger = logging.getLogger(__name__)


class NewsAgent:
    """
    Responsible for collecting and analyzing company news.
    
    Responsibilities:
    - Collect recent news articles
    - Summarize headlines
    - Classify sentiment (positive, neutral, negative)
    - Identify key business events
    - Assess news impact on stock
    """
    
    def __init__(self):
        """Initialize the News Agent"""
        self.name = "News Agent"
        self.news_client = NewsClient()
        self.sentiment = SentimentAnalysis()
        logger.info(f"{self.name} initialized")
    
    def run(self, ticker: str, company_name: str) -> Dict[str, Any]:
        """
        Collect and analyze news for a given ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'JPM')
            company_name: Company full name
        
        Returns:
            Dictionary with news summaries and sentiment
        """
        logger.info(f"Collecting news for {ticker}")
        
        try:
            # Fetch news
            articles = self.news_client.get_news(ticker, company_name, limit=10)
            
            if not articles:
                logger.warning(f"No news found for {ticker}")
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": "No news articles found",
                    "articles": []
                }
            
            # Analyze sentiment for each article
            processed_articles = []
            for article in articles:
                sentiment = NewsClient.get_sentiment_label(
                    article.get("title", "") + " " + article.get("description", "")
                )
                
                article["sentiment"] = sentiment
                processed_articles.append(article)
            
            # Calculate overall sentiment
            overall_sentiment = self._calculate_overall_sentiment(processed_articles)
            
            # Count sentiment distribution
            sentiment_counts = self._count_sentiments(processed_articles)
            
            return {
                "ticker": ticker,
                "success": True,
                "articles": processed_articles,
                "overall_sentiment": overall_sentiment,
                "sentiment_counts": sentiment_counts,
                "total_articles": len(processed_articles)
            }
        
        except Exception as e:
            logger.error(f"Error collecting news: {str(e)}")
            return {
                "ticker": ticker,
                "success": False,
                "error": str(e),
                "articles": []
            }
    
    @staticmethod
    def _calculate_overall_sentiment(articles: list) -> str:
        """Calculate overall sentiment from articles"""
        if not articles:
            return "Neutral"
        
        positive = sum(1 for a in articles if a.get("sentiment") == "Positive")
        negative = sum(1 for a in articles if a.get("sentiment") == "Negative")
        total = len(articles)
        
        positive_pct = (positive / total) * 100 if total > 0 else 0
        negative_pct = (negative / total) * 100 if total > 0 else 0
        
        if positive_pct > 40:
            return "Positive"
        elif negative_pct > 40:
            return "Negative"
        else:
            return "Neutral"
    
    @staticmethod
    def _count_sentiments(articles: list) -> Dict[str, int]:
        """Count sentiment distribution"""
        return {
            "positive": sum(1 for a in articles if a.get("sentiment") == "Positive"),
            "neutral": sum(1 for a in articles if a.get("sentiment") == "Neutral"),
            "negative": sum(1 for a in articles if a.get("sentiment") == "Negative")
        }