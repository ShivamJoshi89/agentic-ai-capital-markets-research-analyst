"""
News client for fetching company news and articles
"""

import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import feedparser
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class NewsClient:
    """
    Client for fetching news articles related to companies.
    Uses Google News RSS as a free fallback.
    """
    
    def __init__(self):
        """Initialize News client"""
        self.name = "News Client"
        logger.info(f"{self.name} initialized")
    
    def get_news(self, ticker: str, company_name: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch recent news articles using Google News RSS.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Full company name
            limit: Number of articles to fetch
        
        Returns:
            List of news articles or empty list if error
        """
        try:
            logger.info(f"Fetching news for {ticker} ({company_name}), limit={limit}")
            
            # Use Google News RSS feed for company name
            # This is a free alternative to NewsAPI
            search_query = f'"{company_name}" OR {ticker}'
            query_params = urlencode({
                "q": search_query,
                "hl": "en-US",
                "gl": "US",
                "ceid": "US:en"
            })
            rss_url = f"https://news.google.com/rss/search?{query_params}"
            
            articles = []
            
            try:
                feed = feedparser.parse(rss_url)
                
                for entry in feed.entries[:limit]:
                    article = {
                        "title": entry.get("title", ""),
                        "description": entry.get("summary", ""),
                        "source": entry.get("source", {}).get("title", "Google News"),
                        "url": entry.get("link", ""),
                        "published_date": entry.get("published", ""),
                        "ticker": ticker
                    }
                    articles.append(article)
                
                logger.info(f"Successfully fetched {len(articles)} articles for {ticker}")
                return articles
            
            except Exception as e:
                logger.warning(f"Error fetching from Google News: {str(e)}")
                return []
        
        except Exception as e:
            logger.error(f"Error in get_news: {str(e)}")
            return []
    
    @staticmethod
    def get_sentiment_label(text: str) -> str:
        """
        Simple sentiment classification based on keywords.
        
        Args:
            text: Text to analyze
        
        Returns:
            Sentiment label: 'Positive', 'Neutral', or 'Negative'
        """
        if not text:
            return "Neutral"
        
        text_lower = text.lower()
        
        positive_keywords = [
            "bullish", "surge", "rally", "jump", "soar", "gain", "beat",
            "profit", "growth", "strong", "rose", "outperform", "upgrade",
            "buy", "positive", "success", "record", "high", "recover"
        ]
        
        negative_keywords = [
            "bearish", "plunge", "crash", "fall", "decline", "loss", "miss",
            "weakness", "weak", "drop", "cut", "downgrade", "sell", "negative",
            "concern", "risk", "slump", "volatile", "loss", "down"
        ]
        
        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)
        
        if positive_count > negative_count:
            return "Positive"
        elif negative_count > positive_count:
            return "Negative"
        else:
            return "Neutral"