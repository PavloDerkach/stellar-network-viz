"""
Data Fetcher Module
Handles data fetching from Stellar API
"""

import streamlit as st
import logging

from src.api.stellar_client import StellarClient

logger = logging.getLogger(__name__)

class DataFetcher:
    """Handles fetching and caching of Stellar network data."""
    
    def __init__(self, client=None):
        """Initialize the data fetcher."""
        self.client = client
    
    @st.cache_data(ttl=3600, show_spinner=False)
    def fetch_network_data(_self, wallet_address: str, max_wallets: int = 100, 
                          strategy: str = "most_active", asset_filter=None,
                          date_from=None, date_to=None, max_pages: int = 50):
        """
        Fetch network data with caching.
        
        Args:
            wallet_address: Starting wallet address
            max_wallets: Maximum number of wallets to fetch
            strategy: Fetching strategy
            asset_filter: Asset filter list
            date_from: Start date filter
            date_to: End date filter
            max_pages: Max pages per wallet
            
        Returns:
            Network data dictionary
        """
        import asyncio
        
        # FIX: Проверяем что asset_filter это список, а не число
        if isinstance(asset_filter, int):
            logger.warning(f"asset_filter is int ({asset_filter}), converting to None")
            asset_filter = None
        elif asset_filter and not isinstance(asset_filter, list):
            asset_filter = [asset_filter] if isinstance(asset_filter, str) else None
        
        async def fetch():
            async with StellarClient() as client:
                # Use depth=0 - ONLY start wallet transactions (ego-graph)
                data = await client.fetch_wallet_network(
                    start_wallet=wallet_address,
                    depth=0,  # Only start wallet - NO partner loading!
                    max_wallets=max_wallets,
                    strategy=strategy,
                    asset_filter=asset_filter,
                    date_from=date_from,
                    date_to=date_to,
                    max_pages=max_pages
                )
                return data
        
        try:
            logger.info(f"Fetching network for {wallet_address[:8]}...")
            logger.info(f"Parameters: max_wallets={max_wallets}, strategy={strategy}, max_pages={max_pages}")
            logger.info(f"Filters: assets={asset_filter}, dates={date_from} to {date_to}")
            logger.info(f"🔍 [fetcher.py] Передаю max_pages={max_pages} в stellar_client")
            
            # Run async fetch
            data = asyncio.run(fetch())
            
            logger.info(f"Fetched {len(data['wallets'])} wallets, {len(data['transactions'])} transactions")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching network data: {e}")
            st.error(f"Failed to fetch network data: {str(e)}")
            return None
    
    def clear_cache(self):
        """Clear all cached data."""
        try:
            st.cache_data.clear()
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
