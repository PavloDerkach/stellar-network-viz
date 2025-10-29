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
    
    # Project paths - DYNAMIC, not hardcoded!
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
    CACHE_DIR: Path = DATA_DIR / "cache"
    DATABASE_DIR: Path = BASE_DIR / "database"
    
    # Database
    DATABASE_URL: Optional[str] = Field(default=None)
    
    # Stellar API
    HORIZON_URL: str = Field(
        default="https://horizon.stellar.org",
        description="Stellar Horizon mainnet URL"
    )
    HORIZON_TESTNET_URL: str = Field(
        default="https://horizon-testnet.stellar.org",
        description="Stellar Horizon testnet URL"
    )
    USE_TESTNET: bool = Field(
        default=False,
        description="Use testnet instead of mainnet"
    )
    
    # API Settings
    API_RATE_LIMIT: int = Field(default=100)
    API_TIMEOUT: int = Field(default=30)
    API_MAX_RETRIES: int = Field(default=3)
    
    # Cache Settings
    CACHE_ENABLED: bool = Field(default=True)
    CACHE_TTL: int = Field(default=3600)  # seconds
    
    # Data Processing - INCREASED LIMITS!
    BATCH_SIZE: int = Field(default=50)
    MAX_WALLETS: Optional[int] = Field(default=200)  # Increased from 100
    MAX_TRANSACTIONS_PER_WALLET: int = Field(default=10000)  # Increased from 200!
    DEFAULT_WALLET_LIMIT: int = Field(default=100)  # Increased from 50
    DEFAULT_MAX_PAGES: int = Field(default=50)  # Increased from implicit 25!
    
    # Visualization
    GRAPH_MAX_NODES: int = Field(default=200)  # Increased from 100
    GRAPH_MAX_EDGES: int = Field(default=1000)  # Increased from 500
    DEFAULT_LAYOUT: str = Field(default="force")
    
    # Performance thresholds
    PERFORMANCE_WARNING_NODES: int = Field(default=150)
    PERFORMANCE_MAX_NODES: int = Field(default=200)
    
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
        # Create directories if they don't exist
        for dir_path in [
            self.DATA_DIR,
            self.RAW_DATA_DIR,
            self.PROCESSED_DATA_DIR,
            self.CACHE_DIR,
            self.DATABASE_DIR
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @property
    def horizon_url(self) -> str:
        """Get the appropriate Horizon URL based on network setting."""
        return self.HORIZON_TESTNET_URL if self.USE_TESTNET else self.HORIZON_URL
    
    @property
    def database_path(self) -> Path:
        """Get database file path."""
        if self.DATABASE_URL:
            # Extract path from URL if provided
            if self.DATABASE_URL.startswith("sqlite:///"):
                return Path(self.DATABASE_URL.replace("sqlite:///", ""))
        return self.DATABASE_DIR / "stellar.db"


# Create global settings instance
settings = Settings()
