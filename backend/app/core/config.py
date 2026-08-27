from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "AI Real-World Investigator"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    # Default to sqlite+aiosqlite for instant local run without external services,
    # or postgresql+asyncpg://postgres:postgres@localhost:5432/investigator
    DATABASE_URL: str = "sqlite+aiosqlite:///./investigator.db"
    
    # LLM Configuration
    DEFAULT_LLM_PROVIDER: str = "gemini"  # gemini, openai, deepseek, mock
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    
    FAST_LLM_MODEL: str = "gemini-1.5-flash"
    REASONING_LLM_MODEL: str = "gemini-1.5-pro"
    
    # Search Configuration
    DEFAULT_SEARCH_PROVIDER: str = "duckduckgo"  # duckduckgo, tavily, mock
    TAVILY_API_KEY: Optional[str] = None
    SERPAPI_API_KEY: Optional[str] = None
    
    # Scraper & Rate Limit Settings
    SCRAPER_TIMEOUT_SECONDS: int = 15
    MAX_SEARCH_QUERIES_PER_INVESTIGATION: int = 5
    MAX_SOURCES_PER_INVESTIGATION: int = 12
    MAX_TEXT_TOKENS_PER_SOURCE: int = 6000
    INVESTIGATION_TIMEOUT_SECONDS: int = 300
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "*"]

settings = Settings()
