"""
config.py — Central configuration loaded from environment variables.

Uses pydantic-settings to validate and type-cast all required env vars.
Values are read from a .env file at the project root (or from the OS environment).
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- LLM ---
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str

    # --- Currency API ---
    EXCHANGE_RATE_API_KEY: str

    # --- Supabase PostgreSQL connection string ---
    # Provided by Supabase Dashboard → Project Settings → Database → Connection string
    DATABASE_URL: str

    # --- Defaults & Limits ---
    FALLBACK_USD_TO_PKR: float = 278.0
    EXCHANGE_RATE_CACHE_HOURS: int = 1       # Refresh rate from ExchangeRate-API
    DEFAULT_MIN_REVIEWS: int = 5
    MAX_PRODUCTS_PER_SITE: int = 20

    class Config:
        env_file = ".env"


settings = Settings()
