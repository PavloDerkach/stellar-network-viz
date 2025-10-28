"""
Project configuration settings.
"""
import os
from pathlib import Path
from typing import Optional

# Try to import from pydantic_settings first (Pydantic v2)
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    PYDANTIC_V2 = True
except ImportError:
    # Fall back to pydantic for older versions
    from pydantic import BaseSettings
    PYDANTIC_V2 = False

from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Configure for Pydantic v2 if available
    if PYDANTIC_V2:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="allow",
            env_prefix=""
        )
    
    # Project paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
    CACHE_DIR: Path = DATA_DIR / "cache"
    DATABASE_DIR: Path = BASE_DIR / "database"
    
    # Database
    DATABASE_URL: str = Field(
        default=None,
        alias="DATABASE_URL" if PYDANTIC_V2 else None,
        env="DATABASE_URL" if not PYDANTIC_V2 else None
    )
    
    # Stellar API
    HORIZON_URL: str = Field(
        default="https://horizon.stellar.org",
        alias="STELLAR_HORIZON_URL" if PYDANTIC_V2 else None,
        env="STELLAR_HORIZON_URL" if not PYDANTIC_V2 else None
    )
    HORIZON_TESTNET_URL: str = Field(
        default="https://horizon-testnet.stellar.org",
        alias="STELLAR_HORIZON_TESTNET_URL" if PYDANTIC_V2 else None,
        env="STELLAR_HORIZON_TESTNET_URL" if not PYDANTIC_V2 else None
    )
    USE_TESTNET: bool = Field(
        default=False,
        alias="USE_TESTNET" if PYDANTIC_V2 else None,
        env="USE_TESTNET" if not PYDANTIC_V2 else None
    )
    
    # API Settings
    API_RATE_LIMIT: int = Field(default=100)
    API_TIMEOUT: int = Field(default=30)
    API_MAX_RETRIES: int = Field(default=3)
    
    # Cache Settings
    CACHE_ENABLED: bool = Field(default=True)
    CACHE_TTL: int = Field(default=3600)  # seconds
    
    # Data Processing
    BATCH_SIZE: int = Field(default=50)
    MAX_WALLETS: Optional[int] = Field(default=100)  # Focus on top 100
    MAX_TRANSACTIONS_PER_WALLET: int = Field(default=200)
    DEFAULT_WALLET_LIMIT: int = Field(default=50)  # Default for UI
    
    # Visualization
    GRAPH_MAX_NODES: int = Field(default=100)  # Support up to 100
    GRAPH_MAX_EDGES: int = Field(default=500)  # More edges for 100 nodes
    DEFAULT_LAYOUT: str = Field(default="force")
    
    # Performance thresholds
    PERFORMANCE_WARNING_NODES: int = Field(default=75)
    PERFORMANCE_MAX_NODES: int = Field(default=100)
    
    # Web App
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8501)
    DEBUG: bool = Field(default=False)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: Optional[str] = Field(default="stellar_viz.log")
    
    # Pydantic v1 configuration
    if not PYDANTIC_V2:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = False
            extra = "allow"
    
    def __init__(self, **kwargs):
        """Initialize settings with defaults."""
        super().__init__(**kwargs)
        # Set default database URL if not provided
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"sqlite:///{self.DATABASE_DIR}/stellar.db"
    
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
