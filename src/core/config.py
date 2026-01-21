from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):

    google_api_key: str

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "stock_trading_agent"

    environment: str = "development"
    debug: bool = True

    max_execution_time_ms: int = 5000
    max_result_size: int = 1000
    max_query_complexity: int = 5

    llm_model: str = "models/gemini-flash-latest"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    allowed_collections: list[str] = ["holdings", "trades"]
    allowed_operations: list[str] = ["find", "aggregate", "countDocuments", "distinct"]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
