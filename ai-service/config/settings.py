from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Smart Mall AI Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    PRODUCT_SERVICE_URL: str = "http://localhost:8081"
    COUPON_SERVICE_URL: str = "http://localhost:8082"
    USER_SERVICE_URL: str = "http://localhost:8083"
    ORDER_SERVICE_URL: str = "http://localhost:8084"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
