#!/usr/bin/env python3
"""
Database setup script for Stellar Network Visualization.
Creates all necessary tables and indexes.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from database.models import Base
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_database():
    """Create database and all tables."""
    logger.info(f"Creating database at: {settings.DATABASE_URL}")
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL, echo=False)
    
    # Create all tables
    logger.info("Creating tables...")
    Base.metadata.create_all(engine)
    
    logger.info("Database setup complete!")
    logger.info("Tables created:")
    for table in Base.metadata.tables:
        logger.info(f"  - {table}")
    
    return engine


def verify_database():
    """Verify that database was created successfully."""
    engine = create_engine(settings.DATABASE_URL)
    
    # Check if tables exist
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    tables = inspector.get_table_names()
    logger.info(f"Found {len(tables)} tables in database:")
    for table in tables:
        columns = inspector.get_columns(table)
        logger.info(f"  {table}: {len(columns)} columns")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Stellar Network Visualization - Database Setup")
    logger.info("=" * 50)
    
    try:
        # Create database
        create_database()
        
        # Verify
        logger.info("\nVerifying database...")
        verify_database()
        
        logger.info("\n✅ Database setup completed successfully!")
        logger.info("You can now run the application with: streamlit run web/app.py")
        
    except Exception as e:
        logger.error(f"❌ Error setting up database: {e}")
        sys.exit(1)
