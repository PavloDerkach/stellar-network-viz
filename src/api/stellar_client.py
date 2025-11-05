"""
Stellar Network API Client
Fixed version with correct depth logic for recursive partner loading
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
import aiohttp
from stellar_sdk import AiohttpClient
from stellar_sdk.server_async import ServerAsync
from stellar_sdk.exceptions import NotFoundError, BadRequestError
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

class StellarClient:
    """Enhanced Stellar API client with recursive network fetching."""
    
    def __init__(self, horizon_url: str = "https://horizon.stellar.org"):
        """Initialize the Stellar client."""
        self.horizon_url = horizon_url
        self.client = None
        self.server = None
        self._session = None
        self.rate_limit_remaining = 3600
        self.rate_limit_reset = None
        self._request_times = []
        self._max_requests_per_second = 10
        self.data_completeness_info = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def connect(self):
        """Establish connection to Stellar network."""
        self.client = AiohttpClient()
        self.server = ServerAsync(horizon_url=self.horizon_url, client=self.client)
    
    async def close(self):
        """Close the connection."""
        if self.client:
            await self.client.close()
    
    async def _rate_limit(self):
        """Simple rate limiting."""
        now = time.time()
        self._request_times = [t for t in self._request_times if now - t < 1]
        
        if len(self._request_times) >= self._max_requests_per_second:
            sleep_time = 1 - (now - self._request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self._request_times.append(now)
    
    async def get_account_info(self, account_id: str) -> Dict[str, Any]:
        """Get account information."""
        try:
            await self._rate_limit()
            account = await self.server.accounts().account_id(account_id).call()
            return {
                "id": account["id"],
                "sequence": account["sequence"],
                "balances": account["balances"],
                "thresholds": account["thresholds"],
                "flags": account["flags"],
                "created_at": account.get("created_at"),
            }
        except NotFoundError:
            logger.warning(f"Account {account_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error fetching account {account_id}: {e}")
            return None
    
    async def get_account_payments_enhanced(
        self,
        account_id: str,
        limit: int = 200,
        order: str = "desc",
        cursor: Optional[str] = None,
        include_failed: bool = False
    ) -> List[Dict[str, Any]]:
        """Get payments with enhanced error handling and pagination support."""
        payments = []
        
        try:
            await self._rate_limit()
            
            builder = self.server.payments().for_account(account_id).limit(limit).order(order)
            
            if cursor:
                builder = builder.cursor(cursor)
            
            if include_failed:
                builder = builder.include_failed_transactions()
            
            response = await builder.call()
            
            for record in response["_embedded"]["records"]:
                if record["type"] in ["payment", "path_payment_strict_send", "path_payment_strict_receive"]:
                    payment = {
                        "id": record["id"],
                        "type": record["type"],
                        "created_at": record["created_at"],
                        "transaction_hash": record["transaction_hash"],
                        "from": record.get("from", record.get("source_account", "")),
                        "to": record.get("to", ""),
                        "amount": float(record.get("amount", 0)),
                        "asset_type": record.get("asset_type", "native"),
                        "asset_code": record.get("asset_code", "XLM"),
                        "asset_issuer": record.get("asset_issuer", ""),
                    }
                    payments.append(payment)
            
            return payments
            
        except Exception as e:
            logger.error(f"Error fetching payments for {account_id}: {e}")
            return []
    
    async def get_all_payments_filtered(
        self,
        account_id: str,
        asset_code: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        max_pages: int = 50
    ) -> List[Dict[str, Any]]:
        """Get ALL payments for account with filters, handling pagination automatically."""
        all_payments = []
        cursor = None
        pages_fetched = 0
        
        # Convert date to datetime if needed for comparison
        from datetime import date as date_type, timezone
        if date_from and isinstance(date_from, date_type) and not isinstance(date_from, datetime):
            date_from = datetime.combine(date_from, datetime.min.time()).replace(tzinfo=timezone.utc)
        if date_to and isinstance(date_to, date_type) and not isinstance(date_to, datetime):
            date_to = datetime.combine(date_to, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        logger.info(f"Fetching {asset_code or 'ALL'} payments for {account_id[:8]}...")
        logger.info(f"🔍 [stellar_client.py] get_all_payments_filtered() вызван с MAX_PAGES={max_pages}")
        if date_from:
            logger.info(f"  Date from: {date_from}")
        if date_to:
            logger.info(f"  Date to: {date_to}")
        
        while pages_fetched < max_pages:
            try:
                await self._rate_limit()
                
                builder = self.server.payments().for_account(account_id).limit(200).order("desc")
                
                if cursor:
                    builder = builder.cursor(cursor)
                
                response = await builder.call()
                records = response["_embedded"]["records"]
                
                if not records:
                    break
                
                batch_payments = []
                for record in records:
                    if record["type"] not in ["payment", "path_payment_strict_send", "path_payment_strict_receive"]:
                        continue
                    
                    created_at = datetime.fromisoformat(record["created_at"].replace('Z', '+00:00'))
                    
                    if date_to and created_at > date_to:
                        continue
                    if date_from and created_at < date_from:
                        logger.info(f"  Reached date limit at {created_at}, stopping pagination")
                        pages_fetched = max_pages
                        break
                    
                    payment_asset = record.get("asset_code", "XLM")
                    if asset_code and payment_asset != asset_code:
                        continue
                    
                    payment = {
                        "id": record["id"],
                        "type": record["type"],
                        "created_at": record["created_at"],
                        "transaction_hash": record["transaction_hash"],
                        "from": record.get("from", record.get("source_account", "")),
                        "to": record.get("to", ""),
                        "amount": float(record.get("amount", 0)),
                        "asset_type": record.get("asset_type", "native"),
                        "asset_code": payment_asset,
                        "asset_issuer": record.get("asset_issuer", ""),
                    }
                    batch_payments.append(payment)
                
                all_payments.extend(batch_payments)
                pages_fetched += 1
                
                if pages_fetched >= max_pages:
                    logger.info(f"  Reached max pages limit ({max_pages})")
                    self.last_fetch_info = {
                        'hit_max_pages': True,
                        'pages_fetched': pages_fetched,
                        'total_payments': len(all_payments)
                    }
                    break
                
                if "next" in response["_links"]:
                    next_href = response["_links"]["next"]["href"]
                    cursor_start = next_href.find("cursor=") + 7
                    cursor_end = next_href.find("&", cursor_start)
                    cursor = next_href[cursor_start:] if cursor_end == -1 else next_href[cursor_start:cursor_end]
                else:
                    break
                
                if pages_fetched % 10 == 0:
                    logger.info(f"  Fetched {pages_fetched} pages, {len(all_payments)} payments so far...")
                
            except Exception as e:
                logger.error(f"Error fetching page {pages_fetched + 1}: {e}")
                break
        
        logger.info(f"  Total: {len(all_payments)} {asset_code or 'ALL'} payments from {pages_fetched} pages")
        
        if pages_fetched >= max_pages:
            logger.warning(f"  ⚠️ Hit page limit! May be missing older transactions")
        
        return all_payments
    
    async def get_account_transactions(
        self, 
        account_id: str,
        limit: int = 200,
        include_failed: bool = False
    ) -> List[Dict[str, Any]]:
        """Get account transactions."""
        transactions = []
        
        try:
            await self._rate_limit()
            
            builder = self.server.transactions().for_account(account_id).limit(limit)
            if include_failed:
                builder = builder.include_failed_transactions()
            
            response = await builder.call()
            
            for tx in response["_embedded"]["records"]:
                transactions.append({
                    "id": tx["id"],
                    "hash": tx["hash"],
                    "ledger": tx["ledger"],
                    "created_at": tx["created_at"],
                    "fee_charged": tx.get("fee_charged", 0),
                    "operation_count": tx["operation_count"],
                    "memo_type": tx.get("memo_type"),
                    "memo": tx.get("memo"),
                    "successful": tx.get("successful", True),
                })
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error fetching transactions for {account_id}: {e}")
            return []
    
    async def get_transaction_details(self, tx_hash: str) -> Dict[str, Any]:
        """Get detailed transaction information."""
        try:
            await self._rate_limit()
            
            tx = await self.server.transactions().transaction(tx_hash).call()
            ops = await self.server.operations().for_transaction(tx_hash).call()
            
            operations = []
            for op in ops["_embedded"]["records"]:
                operations.append({
                    "id": op["id"],
                    "type": op["type"],
                    "created_at": op["created_at"],
                    "details": {k: v for k, v in op.items() 
                               if k not in ["_links", "self", "transaction", "effects", "succeeds", "precedes"]}
                })
            
            return {
                "hash": tx["hash"],
                "ledger": tx["ledger"],
                "created_at": tx["created_at"],
                "source_account": tx["source_account"],
                "fee_charged": tx.get("fee_charged", 0),
                "operation_count": tx["operation_count"],
                "operations": operations,
                "memo_type": tx.get("memo_type"),
                "memo": tx.get("memo"),
                "successful": tx.get("successful", True),
            }
            
        except Exception as e:
            logger.error(f"Error fetching transaction {tx_hash}: {e}")
            return None
    
    async def fetch_wallet_network(
        self,
        start_wallet: str,
        depth: int = 2,
        max_wallets: int = 100,
        strategy: str = "most_active",
        asset_filter: Optional[List[str]] = None,
        tx_type_filter: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        direction_filter: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        max_pages: int = 50
    ) -> Dict[str, Any]:
        """
        Fetch network of wallets connected to a starting wallet.
        
        Args:
            start_wallet: Starting wallet address
            depth: How many hops from start wallet to explore
            max_wallets: Maximum number of wallets to fetch
            strategy: "most_active" or "breadth_first"
            asset_filter: List of assets to filter by (e.g., ["USDC", "XLM"])
            tx_type_filter: List of transaction types to filter by
            date_from: Start date for transaction filtering
            date_to: End date for transaction filtering
            direction_filter: Filter by "Sent" or "Received" from start wallet
            min_amount: Minimum transaction amount
            max_amount: Maximum transaction amount
            max_pages: Maximum pages to fetch per wallet (200 tx per page)
            direction_filter: Filter by "Sent" or "Received" from start wallet
            min_amount: Minimum transaction amount
            max_amount: Maximum transaction amount
            
        Returns:
            Network data with wallets and transactions
        """
        wallet_activity = {}
        transactions = []
        visited = set()
        
        await self._collect_wallet_activity(
            start_wallet, 
            wallet_activity, 
            transactions, 
            visited, 
            depth, 
            max_wallets * 2,
            asset_filter=asset_filter,
            date_from=date_from,
            date_to=date_to,
            max_pages=max_pages
        )
        
        logger.info(f"\n{'='*50}")
        logger.info(f"TRANSACTION FILTERING")
        logger.info(f"{'='*50}")
        logger.info(f"Total collected transactions: {len(transactions)}")
        logger.info(f"Total collected wallets: {len(wallet_activity)}")
        
        # НОВАЯ ЛОГИКА: Приоритет прямым связям стартового кошелька
        direct_partners = set()
        start_tx_count = 0
        
        # Найдём всех прямых партнёров стартового кошелька
        for tx in transactions:
            if tx['from'] == start_wallet:
                direct_partners.add(tx['to'])
                start_tx_count += 1
            elif tx['to'] == start_wallet:
                direct_partners.add(tx['from'])
                start_tx_count += 1
        
        logger.info(f"Start wallet has {start_tx_count} transactions with {len(direct_partners)} unique partners")
        logger.info(f"Current wallet_activity before adding partners: {list(wallet_activity.keys())}")
        
        # КРИТИЧНО для depth=0: Добавляем партнёров в wallet_activity!
        partners_added = 0
        for partner in direct_partners:
            if partner not in wallet_activity:
                # Подсчитаем статистику по транзакциям партнёра
                partner_tx_count = 0
                partner_volume = 0
                partner_counterparties = set()
                
                for tx in transactions:
                    if tx['from'] == partner or tx['to'] == partner:
                        partner_tx_count += 1
                        partner_volume += tx.get('amount', 0)
                        if tx['from'] == partner:
                            partner_counterparties.add(tx['to'])
                        if tx['to'] == partner:
                            partner_counterparties.add(tx['from'])
                
                wallet_activity[partner] = {
                    "transaction_count": partner_tx_count,
                    "total_volume": partner_volume,
                    "counterparties": partner_counterparties,
                    "has_direct_tx_with_start": True
                }
                partners_added += 1
                logger.info(f"  Added partner {partner[:8]}... to wallet_activity ({partner_tx_count} txs)")
        
        logger.info(f"✅ Added {partners_added} partners. Total wallets now: {len(wallet_activity)}")
        
        # Помечаем прямых партнёров
        for wallet_id in direct_partners:
            if wallet_id in wallet_activity:
                wallet_activity[wallet_id]['has_direct_tx_with_start'] = True
                
        # Отбираем топ кошельки с ПРИОРИТЕТОМ прямых связей
        if strategy == "most_active":
            # СНАЧАЛА берём ВСЕ прямые связи
            top_wallets = list(direct_partners)
            logger.info(f"Including ALL {len(direct_partners)} direct partners first")
            
            # ПОТОМ добавляем самые активные из остальных
            if len(top_wallets) < max_wallets:
                other_wallets = [(w, data) for w, data in wallet_activity.items() 
                                 if w not in direct_partners]
                other_wallets.sort(key=lambda x: x[1]["transaction_count"], reverse=True)
                
                remaining_slots = max_wallets - len(top_wallets)
                for wallet_id, _ in other_wallets[:remaining_slots]:
                    top_wallets.append(wallet_id)
                    
                logger.info(f"Added {min(remaining_slots, len(other_wallets))} additional active wallets")
        else:
            # breadth_first - но всё равно включаем прямые связи первыми
            top_wallets = list(direct_partners)[:max_wallets]
            if len(top_wallets) < max_wallets:
                for wallet_id in wallet_activity.keys():
                    if wallet_id not in direct_partners:
                        top_wallets.append(wallet_id)
                        if len(top_wallets) >= max_wallets:
                            break
        
        logger.info(f"Top wallets selected: {len(top_wallets)}")
        
        # Проверяем что GDT7...GULJ включён (если есть)
        gulj_wallet = None
        for wallet in top_wallets:
            if wallet.startswith("GDT7") and "GULJ" in wallet:
                gulj_wallet = wallet
                logger.info(f"✅ CONFIRMED: {gulj_wallet[:8]}...{gulj_wallet[-4:]} is in top wallets!")
                break
        
        # Фильтруем транзакции
        filtered_transactions = []
        for tx in transactions:
            # КРИТИЧНО: Оставляем ТОЛЬКО транзакции стартового кошелька!
            if tx["from"] == start_wallet or tx["to"] == start_wallet:
                # Apply additional filters
                if direction_filter:
                    if direction_filter == "Sent" and tx["from"] != start_wallet:
                        continue
                    if direction_filter == "Received" and tx["to"] != start_wallet:
                        continue
                
                if min_amount and tx["amount"] < min_amount:
                    continue
                if max_amount and tx["amount"] > max_amount:
                    continue
                
                filtered_transactions.append(tx)
        
        logger.info(f"Filtered transactions: {len(transactions)} -> {len(filtered_transactions)}")
        
        # Get details for top wallets
        wallet_details = {}
        for wallet_id in top_wallets:
            details = wallet_activity.get(wallet_id, {
                "transaction_count": 0,
                "total_volume": 0,
                "counterparties": set()
            })
            
            # Mark if it's a direct partner
            is_direct = wallet_id in direct_partners
            
            wallet_details[wallet_id] = {
                "id": wallet_id,
                "transaction_count": details["transaction_count"],
                "total_volume": details["total_volume"],
                "unique_counterparties": len(details["counterparties"]),
                "is_direct_partner": is_direct,
                "has_direct_tx_with_start": details.get('has_direct_tx_with_start', False)
            }
        
        # Calculate unique wallets
        unique_wallets = set()
        for tx in filtered_transactions:
            unique_wallets.add(tx["from"])
            unique_wallets.add(tx["to"])
        
        logger.info(f"Total unique wallets in filtered transactions: {len(unique_wallets)}")
        
        # Add filtering stats
        filtering_stats = {
            "total_discovered_wallets": len(wallet_activity),
            "total_discovered_transactions": len(transactions),
            "direct_partners_count": len(direct_partners),
            "top_wallets_selected": len(top_wallets),
            "filtered_transactions": len(filtered_transactions),
            "unique_wallets_in_result": len(unique_wallets)
        }
        
        # Add data completeness info
        data_completeness = self.data_completeness_info.copy() if hasattr(self, 'data_completeness_info') else {}
        self.data_completeness_info = {}
        
        return {
            "wallets": wallet_details,
            "transactions": filtered_transactions,
            "stats": {
                "total_wallets": len(wallet_details),
                "total_transactions": len(filtered_transactions),
                "depth_explored": depth,
                "wallets_discovered": len(wallet_activity),
                "strategy": strategy,
                "filtering_stats": filtering_stats,
                "data_completeness": data_completeness
            }
        }
    
    async def _collect_wallet_activity(
        self,
        wallet_id: str,
        wallet_activity: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        visited: set,
        max_depth: int,
        max_collect: int,
        current_depth: int = 0,
        asset_filter: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        max_pages: int = 50
    ):
        """
        Collect wallet activity data recursively WITH FILTERS and PAGINATION.
        
        Gets ALL transactions for the specified period and asset!
        """
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: изменено >= на >
        # EGO-GRAPH MODE: depth=0 загружает ТОЛЬКО стартовый кошелёк
        if current_depth > max_depth or len(wallet_activity) >= max_collect:
            return
        
        if wallet_id in visited:
            return
        
        visited.add(wallet_id)
        
        # Initialize wallet activity tracking
        if wallet_id not in wallet_activity:
            wallet_activity[wallet_id] = {
                "transaction_count": 0,
                "total_volume": 0,
                "counterparties": set()
            }
        
        # Fetch ALL payments with filters and pagination
        try:
            # Determine which asset to filter by
            # If multiple assets in filter, fetch for each
            assets_to_fetch = asset_filter if asset_filter and "All" not in asset_filter else [None]
            
            logger.info(f"===== Collecting activity for {wallet_id[:8]} =====")
            logger.info(f"Asset filter received: {asset_filter}")
            logger.info(f"Assets to fetch: {assets_to_fetch}")
            logger.info(f"Date range: {date_from} to {date_to}")
            logger.info(f"Current depth: {current_depth}/{max_depth}")
            
            all_payments = []
            for asset_code in assets_to_fetch:
                logger.info(f"Fetching {asset_code or 'ALL'} payments for {wallet_id[:8]}...")
                
                payments = await self.get_all_payments_filtered(
                    account_id=wallet_id,
                    asset_code=asset_code,
                    date_from=date_from,
                    date_to=date_to,
                    max_pages=max_pages
                )
                
                logger.info(f"Got {len(payments)} payments for asset {asset_code or 'ALL'}")
                all_payments.extend(payments)
                
                # Сохраняем информацию о полноте для этого кошелька
                if hasattr(self, 'last_fetch_info') and self.last_fetch_info:
                    if wallet_id not in self.data_completeness_info:
                        self.data_completeness_info[wallet_id] = []
                    self.data_completeness_info[wallet_id].append({
                        'asset': asset_code or 'ALL',
                        **self.last_fetch_info
                    })
                    self.last_fetch_info = None
            
            logger.info(f"Got {len(all_payments)} payments total for {wallet_id[:8]}")
            
            # Process payments
            tx_added = 0
            for payment in all_payments:
                from_wallet = payment["from"]
                to_wallet = payment["to"]
                amount = payment["amount"]
                
                # Skip if neither wallet is in our target set
                if from_wallet == wallet_id or to_wallet == wallet_id:
                    # Add transaction to global list (avoid duplicates)
                    tx_key = f"{payment['transaction_hash']}_{from_wallet}_{to_wallet}"
                    if not any(tx.get('transaction_hash') == payment['transaction_hash'] and 
                              tx.get('from') == from_wallet and tx.get('to') == to_wallet 
                              for tx in transactions):
                        transactions.append(payment)
                        tx_added += 1
                    
                    # Update wallet activity
                    for w in [from_wallet, to_wallet]:
                        if w not in wallet_activity:
                            wallet_activity[w] = {
                                "transaction_count": 0,
                                "total_volume": 0,
                                "counterparties": set()
                            }
                        
                        wallet_activity[w]["transaction_count"] += 1
                        wallet_activity[w]["total_volume"] += amount
                    
                    # Track counterparties
                    wallet_activity[from_wallet]["counterparties"].add(to_wallet)
                    wallet_activity[to_wallet]["counterparties"].add(from_wallet)
                    
                    # Explore connected wallets (only if depth allows)
                    if current_depth < max_depth:
                        for next_wallet in [from_wallet, to_wallet]:
                            if next_wallet != wallet_id and next_wallet not in visited and len(wallet_activity) < max_collect:
                                await self._collect_wallet_activity(
                                    next_wallet,
                                    wallet_activity,
                                    transactions,
                                    visited,
                                    max_depth,
                                    max_collect,
                                    current_depth + 1,
                                    asset_filter=asset_filter,
                                    date_from=date_from,
                                    date_to=date_to,
                                    max_pages=max_pages
                                )
            
            logger.info(f"✅ Added {tx_added} transactions from {wallet_id[:8]} to global list")
            
        except Exception as e:
            logger.warning(f"Error collecting activity for {wallet_id}: {e}")
    
    async def fetch_top_active_wallets(
        self,
        limit: int = 100,
        time_period: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch the most active wallets from the network.
        
        Args:
            limit: Number of top wallets to fetch
            time_period: Time period in days (None for all time)
            
        Returns:
            Network data with top active wallets
        """
        logger.info(f"Fetching top {limit} active wallets...")
        
        seed_wallets = [
            "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN7",
        ]
        
        wallet_activity = {}
        all_transactions = []
        
        for seed in seed_wallets:
            data = await self.fetch_wallet_network(
                seed,
                depth=3,
                max_wallets=limit,
                strategy="most_active"
            )
            
            for wallet_id, details in data["wallets"].items():
                if wallet_id not in wallet_activity:
                    wallet_activity[wallet_id] = details
            
            all_transactions.extend(data["transactions"])
        
        sorted_wallets = sorted(
            wallet_activity.items(),
            key=lambda x: x[1].get("transaction_count", 0),
            reverse=True
        )
        
        top_wallets = dict(sorted_wallets[:limit])
        
        return {
            "wallets": top_wallets,
            "transactions": all_transactions,
            "stats": {
                "total_wallets": len(top_wallets),
                "total_transactions": len(all_transactions),
                "sampling_seeds": len(seed_wallets),
                "start_wallet": start_wallet,  # КРИТИЧНО: стартовый кошелёк
            }
        }
