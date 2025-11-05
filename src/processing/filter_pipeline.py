"""Centralized filter pipeline for transaction processing."""
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class FilterPipeline:
    """Pipeline for applying filters to transactions."""
    
    def __init__(self):
        """Initialize filter pipeline."""
        self.filters: List[Callable] = []
        self.stats = {
            "initial": 0,
            "final": 0,
            "filtered_by": {}
        }
    
    def add_filter(self, filter_func: Callable, name: str = None):
        """Add filter to pipeline."""
        filter_func._name = name or filter_func.__name__
        self.filters.append(filter_func)
    
    def apply(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply all filters to transactions."""
        self.stats["initial"] = len(transactions)
        result = transactions
        
        for filter_func in self.filters:
            before = len(result)
            result = filter_func(result)
            after = len(result)
            
            if before != after:
                filter_name = getattr(filter_func, "_name", "unknown")
                self.stats["filtered_by"][filter_name] = before - after
                logger.info(f"Filter '{filter_name}': {before} → {after} (-{before-after})")
        
        self.stats["final"] = len(result)
        logger.info(f"Pipeline complete: {self.stats['initial']} → {self.stats['final']} transactions")
        
        return result
    
    @staticmethod
    def create_asset_filter(assets: List[str]) -> Callable:
        """Create asset filter function."""
        def filter_by_asset(txs: List[Dict]) -> List[Dict]:
            if not assets or "All" in assets:
                return txs
            return [tx for tx in txs if tx.get("asset_code", "XLM") in assets]
        return filter_by_asset
    
    @staticmethod
    def create_type_filter(tx_types: List[str]) -> Callable:
        """Create transaction type filter."""
        def filter_by_type(txs: List[Dict]) -> List[Dict]:
            if not tx_types or "All" in tx_types:
                return txs
            return [tx for tx in txs if tx.get("type") in tx_types]
        return filter_by_type
    
    @staticmethod
    def create_date_filter(date_from: Optional[date], date_to: Optional[date]) -> Callable:
        """Create date range filter."""
        def filter_by_date(txs: List[Dict]) -> List[Dict]:
            if not date_from and not date_to:
                return txs
            
            filtered = []
            for tx in txs:
                tx_date_str = tx.get("created_at")
                if not tx_date_str:
                    filtered.append(tx)
                    continue
                
                try:
                    tx_date = datetime.fromisoformat(tx_date_str.replace('Z', '+00:00'))
                    
                    if date_from and tx_date.date() < date_from:
                        continue
                    if date_to and tx_date.date() > date_to:
                        continue
                    
                    filtered.append(tx)
                except:
                    filtered.append(tx)
            
            return filtered
        return filter_by_date
    
    @staticmethod
    def create_amount_filter(min_amount: Optional[float], max_amount: Optional[float]) -> Callable:
        """Create amount range filter."""
        def filter_by_amount(txs: List[Dict]) -> List[Dict]:
            if min_amount is None and max_amount is None:
                return txs
            
            filtered = []
            for tx in txs:
                amount = float(tx.get("amount", 0))
                
                if min_amount is not None and amount < min_amount:
                    continue
                if max_amount is not None and amount > max_amount:
                    continue
                
                filtered.append(tx)
            
            return filtered
        return filter_by_amount
    
    @staticmethod
    def create_wallet_filter(wallets: List[str], mode: str = "any") -> Callable:
        """
        Create wallet filter.
        
        Args:
            wallets: List of wallet addresses
            mode: "any" - at least one party in list, "both" - both parties in list
        """
        def filter_by_wallet(txs: List[Dict]) -> List[Dict]:
            if not wallets:
                return txs
            
            wallet_set = set(wallets)
            
            if mode == "both":
                return [
                    tx for tx in txs
                    if tx.get("from") in wallet_set and tx.get("to") in wallet_set
                ]
            else:  # mode == "any"
                return [
                    tx for tx in txs
                    if tx.get("from") in wallet_set or tx.get("to") in wallet_set
                ]
        return filter_by_wallet
    
    @staticmethod
    def create_direction_filter(start_wallet: str, directions: List[str]) -> Callable:
        """Create direction filter relative to start wallet."""
        def filter_by_direction(txs: List[Dict]) -> List[Dict]:
            if not directions or "All" in directions:
                return txs
            
            filtered = []
            for tx in txs:
                is_sent = tx.get("from") == start_wallet
                is_received = tx.get("to") == start_wallet
                
                if "Sent" in directions and is_sent:
                    filtered.append(tx)
                elif "Received" in directions and is_received:
                    filtered.append(tx)
            
            return filtered
        return filter_by_direction
    
    @classmethod
    def create_standard_pipeline(
        cls,
        asset_filter: List[str] = None,
        tx_type_filter: List[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        wallets: List[str] = None,
        start_wallet: str = None,
        direction_filter: List[str] = None
    ) -> "FilterPipeline":
        """Create standard filter pipeline with common filters."""
        pipeline = cls()
        
        # Add filters in order of efficiency (most restrictive first)
        if wallets:
            pipeline.add_filter(cls.create_wallet_filter(wallets), "wallet_filter")
        
        if asset_filter:
            pipeline.add_filter(cls.create_asset_filter(asset_filter), "asset_filter")
        
        if tx_type_filter:
            pipeline.add_filter(cls.create_type_filter(tx_type_filter), "type_filter")
        
        if date_from or date_to:
            pipeline.add_filter(cls.create_date_filter(date_from, date_to), "date_filter")
        
        if min_amount is not None or max_amount is not None:
            pipeline.add_filter(cls.create_amount_filter(min_amount, max_amount), "amount_filter")
        
        if start_wallet and direction_filter:
            pipeline.add_filter(cls.create_direction_filter(start_wallet, direction_filter), "direction_filter")
        
        return pipeline
