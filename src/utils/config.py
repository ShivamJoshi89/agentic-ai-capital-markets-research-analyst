"""
Application configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    
    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    REPORTS_DIR = DATA_DIR / "reports"
    OUTPUTS_DIR = PROJECT_ROOT / "outputs"
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    FRED_API_KEY = os.getenv("FRED_API_KEY")
    
    # Settings
    APP_ENV = os.getenv("APP_ENV", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # yfinance
    YFINANCE_PERIOD = "1y"
    YFINANCE_INTERVAL = "1d"
    
    # Data retention
    CACHE_ENABLED = True
    CACHE_TTL = 3600  # seconds