#!/usr/bin/env python3
"""
Fetch initial data for Stellar Network Visualization.
Downloads sample data from Stellar network for demonstration.
"""
import sys
import asyncio
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.api.stellar_client import StellarClient, StellarDataFetcher
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_sample_data():
    """Fetch sample data from Stellar network."""
    logger.info("Initializing Stellar client...")
    client = StellarClient()
    fetcher = StellarDataFetcher(client)
    
    # Sample wallets to analyze (testnet examples)
    sample_wallets = [
        "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN7",  # Friendbot
        # Add more known active wallets here
    ]
    
    all_data = {
        "wallets": {},
        "transactions": [],
        "metadata": {
            "fetched_at": datetime.utcnow().isoformat(),
            "network": "testnet" if settings.USE_TESTNET else "mainnet"
        }
    }
    
    for wallet in sample_wallets:
        logger.info(f"Fetching data for wallet: {wallet[:8]}...")
        
        try:
            # Fetch network around this wallet
            data = await fetcher.fetch_wallet_network(
                wallet,
                depth=2,
                max_wallets=50,
                strategy="most_active"
            )
            
            # Merge data
            all_data["wallets"].update(data["wallets"])
            all_data["transactions"].extend(data["transactions"])
            
            logger.info(f"  Found {len(data['wallets'])} wallets and {len(data['transactions'])} transactions")
            
        except Exception as e:
            logger.error(f"  Error fetching data for {wallet}: {e}")
    
    # Remove duplicate transactions
    unique_txs = {tx.get("transaction_hash", str(i)): tx for i, tx in enumerate(all_data["transactions"])}
    all_data["transactions"] = list(unique_txs.values())
    
    logger.info(f"\nTotal collected:")
    logger.info(f"  - Wallets: {len(all_data['wallets'])}")
    logger.info(f"  - Transactions: {len(all_data['transactions'])}")
    
    return all_data


async def save_sample_data(data: dict):
    """Save sample data to file."""
    output_dir = settings.PROCESSED_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"sample_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Convert datetime objects to strings
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        return str(obj)
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=json_serializer)
    
    logger.info(f"Sample data saved to: {output_file}")
    
    # Also save a "latest" version
    latest_file = output_dir / "sample_data_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(data, f, indent=2, default=json_serializer)
    
    logger.info(f"Latest data saved to: {latest_file}")


async def main():
    """Main function."""
    logger.info("=" * 50)
    logger.info("Stellar Network Visualization - Initial Data Fetch")
    logger.info("=" * 50)
    logger.info(f"Network: {'TESTNET' if settings.USE_TESTNET else 'MAINNET'}")
    logger.info("")
    
    try:
        # Fetch data
        logger.info("Fetching sample data from Stellar network...")
        data = await fetch_sample_data()
        
        # Save data
        logger.info("\nSaving data...")
        await save_sample_data(data)
        
        logger.info("\n✅ Initial data fetch completed successfully!")
        logger.info("You can now run the application with: streamlit run web/app.py")
        
    except Exception as e:
        logger.error(f"❌ Error fetching initial data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run async main function
    asyncio.run(main())
