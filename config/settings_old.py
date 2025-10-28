"""
Project configuration settings.
"""
import os
from pathlib import Path
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Project paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
    CACHE_DIR: Path = DATA_DIR / "cache"
    DATABASE_DIR: Path = BASE_DIR / "database"
    
    # Database
    DATABASE_URL: str = Field(
        default=f"sqlite:///{DATABASE_DIR}/stellar.db",
        env="DATABASE_URL"
    )
    
    # Stellar API
    HORIZON_URL: str = Field(
        default="https://horizon.stellar.org",
        env="STELLAR_HORIZON_URL"
    )
    HORIZON_TESTNET_URL: str = Field(
        default="https://horizon-testnet.stellar.org",
        env="STELLAR_HORIZON_TESTNET_URL"
    )
    USE_TESTNET: bool = Field(default=False, env="USE_TESTNET")
    
    # API Settings
    API_RATE_LIMIT: int = Field(default=100, env="API_RATE_LIMIT")
    API_TIMEOUT: int = Field(default=30, env="API_TIMEOUT")
    API_MAX_RETRIES: int = Field(default=3, env="API_MAX_RETRIES")
    
    # Cache Settings
    CACHE_ENABLED: bool = Field(default=True, env="CACHE_ENABLED")
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")  # seconds
    
# Data Processing
    BATCH_SIZE: int = Field(default=50, env="BATCH_SIZE")
    MAX_WALLETS: Optional[int] = Field(default=100, env="MAX_WALLETS")  # Focus on top 100
    MAX_TRANSACTIONS_PER_WALLET: int = Field(default=200, env="MAX_TRANSACTIONS_PER_WALLET")
    DEFAULT_WALLET_LIMIT: int = Field(default=50, env="DEFAULT_WALLET_LIMIT")  # Default for UI
    
    # Visualization
    GRAPH_MAX_NODES: int = Field(default=100, env="GRAPH_MAX_NODES")  # Support up to 100
    GRAPH_MAX_EDGES: int = Field(default=500, env="GRAPH_MAX_EDGES")  # More edges for 100 nodes
    
    # Performance thresholds
    PERFORMANCE_WARNING_NODES: int = Field(default=75, env="PERFORMANCE_WARNING_NODES")
    PERFORMANCE_MAX_NODES: int = Field(default=100, env="PERFORMANCE_MAX_NODES")
    DEFAULT_LAYOUT: str = Field(default="force", env="DEFAULT_LAYOUT")
    
    # Web App
    APP_HOST: str = Field(default="0.0.0.0", env="APP_HOST")
    APP_PORT: int = Field(default=8501, env="APP_PORT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default="stellar_viz.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def horizon_url(self) -> str:
        """Get the appropriate Horizon URL based on network setting."""
        return self.HORIZON_TESTNET_URL if self.USE_TESTNET else self.HORIZON_URL
    
    def create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        for dir_path in [
            self.DATA_DIR,
            self.RAW_DATA_DIR,
            self.PROCESSED_DATA_DIR,
            self.CACHE_DIR,
            self.DATABASE_DIR
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


# Create global settings instance
settings = Settings()
settings.create_directories()
