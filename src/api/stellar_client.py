"""
Stellar Horizon API client for fetching blockchain data.
"""
import asyncio
from datetime import datetime, timedelta, date, time
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
import logging
from decimal import Decimal

import aiohttp
from stellar_sdk import Server, Asset as StellarAsset
from stellar_sdk.exceptions import NotFoundError, BadRequestError
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import settings

logger = logging.getLogger(__name__)


class StellarClient:
    """Client for interacting with Stellar Horizon API."""
    
    def __init__(self, horizon_url: Optional[str] = None):
        """
        Initialize Stellar client.
        
        Args:
            horizon_url: Custom Horizon server URL (uses settings default if None)
        """
        self.horizon_url = horizon_url or settings.horizon_url
        self.server = Server(horizon_url=self.horizon_url)
        self.session = self._create_session()
        self.rate_limiter = RateLimiter(settings.API_RATE_LIMIT)
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=settings.API_MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    async def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch account details from Stellar network.
        
        Args:
            account_id: Stellar account ID
            
        Returns:
            Account data or None if not found
        """
        try:
            await self.rate_limiter.acquire()
            account = self.server.accounts().account_id(account_id).call()
            return self._process_account_data(account)
        except NotFoundError:
            # Старые удалённые кошельки - это нормально, не ошибка
            logger.debug(f"Account not found (may be deleted/merged): {account_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching account {account_id}: {e}")
            return None
    
    async def get_transactions(
        self,
        account_id: str,
        limit: int = 200,
        order: str = "desc",
        cursor: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch transactions for an account.
        
        Args:
            account_id: Stellar account ID
            limit: Maximum number of transactions to fetch
            order: Order of results ('asc' or 'desc')
            cursor: Pagination cursor
            
        Returns:
            List of transaction data
        """
        try:
            await self.rate_limiter.acquire()
            
            builder = self.server.transactions().for_account(account_id)
            builder.limit(min(limit, 200))  # API max is 200
            builder.order(order)
            
            if cursor:
                builder.cursor(cursor)
            
            response = builder.call()
            return [self._process_transaction_data(tx) for tx in response["_embedded"]["records"]]
            
        except Exception as e:
            logger.error(f"Error fetching transactions for {account_id}: {e}")
            return []
    
    async def get_payments(
        self,
        account_id: str,
        limit: int = 200,
        include_failed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetch payment operations for an account.
        
        Args:
            account_id: Stellar account ID
            limit: Maximum number of payments to fetch
            include_failed: Whether to include failed operations
            
        Returns:
            List of payment data
        """
        try:
            await self.rate_limiter.acquire()
            
            builder = self.server.payments().for_account(account_id)
            builder.limit(min(limit, 200))
            
            if include_failed:
                builder.include_failed(True)
            
            response = builder.call()
            payments = []
            
            for payment in response["_embedded"]["records"]:
                if payment["type"] in ["payment", "create_account", "path_payment_strict_send", "path_payment_strict_receive"]:
                    payments.append(self._process_payment_data(payment))
            
            return payments
            
        except Exception as e:
            logger.error(f"Error fetching payments for {account_id}: {e}")
            return []
    
    async def get_all_payments_filtered(
        self,
        account_id: str,
        asset_code: Optional[str] = None,
        asset_issuer: Optional[str] = None,
        date_from: Union[datetime, date, None] = None,
        date_to: Union[datetime, date, None] = None,
        max_pages: int = 1000,  # Защита от бесконечного цикла
        include_failed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetch ALL payment operations for an account with pagination and filters.
        
        Args:
            account_id: Stellar account ID
            asset_code: Filter by asset code (e.g., "USDC", "XLM")
            asset_issuer: Filter by asset issuer
            date_from: Start date for filtering
            date_to: End date for filtering
            max_pages: Maximum number of pages to fetch (safety limit)
            include_failed: Whether to include failed operations
            
        Returns:
            List of ALL filtered payment data
        """
        # Convert date objects to datetime if needed
        if date_from is not None and isinstance(date_from, date) and not isinstance(date_from, datetime):
            date_from = datetime.combine(date_from, time.min)
        if date_to is not None and isinstance(date_to, date) and not isinstance(date_to, datetime):
            date_to = datetime.combine(date_to, time.max)
        
        all_payments = []
        cursor = None
        page_count = 0
        
        logger.info(f"Fetching ALL payments for {account_id[:8]}... (asset: {asset_code or 'ALL'})")
        
        try:
            while page_count < max_pages:
                await self.rate_limiter.acquire()
                
                # Build request
                builder = self.server.payments().for_account(account_id)
                builder.limit(200)  # Maximum per request
                
                if cursor:
                    builder.cursor(cursor)
                
                if include_failed:
                    builder.include_failed(True)
                
                # Fetch page
                response = builder.call()
                records = response.get("_embedded", {}).get("records", [])
                
                if not records:
                    break
                
                # Process and filter payments
                page_payments = []
                page_stats = {"payment": 0, "create_account": 0, "path_payment_strict_send": 0, "path_payment_strict_receive": 0}
                filtered_out = {"asset": 0, "date": 0}
                sample_assets = []  # Для примера что приходит
                
                for payment in records:
                    if payment["type"] not in ["payment", "create_account", "path_payment_strict_send", "path_payment_strict_receive"]:
                        continue
                    
                    page_stats[payment["type"]] = page_stats.get(payment["type"], 0) + 1
                    
                    processed = self._process_payment_data(payment)
                    
                    # Логируем первые 3 примера asset_code
                    if len(sample_assets) < 3:
                        sample_assets.append({
                            "type": payment["type"],
                            "asset": processed.get("asset_code"),
                            "raw_asset": payment.get("asset_code"),
                            "raw_dest_asset": payment.get("destination_asset_code")
                        })
                    
                    # Filter by asset
                    if asset_code and processed.get("asset_code") != asset_code:
                        filtered_out["asset"] += 1
                        continue
                    
                    if asset_issuer and processed.get("asset_issuer") != asset_issuer:
                        filtered_out["asset"] += 1
                        continue
                    
                    # Filter by date
                    created_at = processed.get("created_at")
                    if created_at:
                        if date_from and created_at < date_from:
                            filtered_out["date"] += 1
                            continue
                        if date_to and created_at > date_to:
                            filtered_out["date"] += 1
                            continue
                    
                    page_payments.append(processed)
                
                if page_count == 0:  # Логируем только для первой страницы
                    logger.info(f"Page stats: {page_stats} | Matched after filter: {len(page_payments)}")
                    logger.info(f"Filtered out - by asset: {filtered_out['asset']}, by date: {filtered_out['date']}")
                    logger.info(f"Looking for asset: {asset_code}")
                    logger.info(f"Sample assets from API: {sample_assets}")
                
                all_payments.extend(page_payments)
                page_count += 1
                
                # Check if we got less than 200 records (end of data)
                if len(records) < 200:
                    logger.info(f"Fetched {len(all_payments)} payments in {page_count} pages (end reached)")
                    break
                
                # Get cursor for next page
                cursor = records[-1].get("paging_token")
                
                # Progress logging
                if page_count % 10 == 0:
                    logger.info(f"Progress: {page_count} pages, {len(all_payments)} payments so far...")
            
            # Показываем warning ТОЛЬКО если реально достигнут лимит (не закончились данные)
            if page_count >= max_pages and len(records) == 200:
                logger.warning(f"⚠️ LIMIT REACHED! Got {len(all_payments)} transactions in {max_pages} pages. Wallet may have MORE data!")
                logger.warning(f"→ Consider increasing 'Max transactions per wallet' in sidebar")
            
            logger.info(f"Total: {len(all_payments)} filtered payments from {page_count} pages")
            return all_payments
            
        except Exception as e:
            logger.error(f"Error fetching all payments for {account_id}: {e}")
            return all_payments  # Return what we got so far
    
    async def get_network_stats(self) -> Dict[str, Any]:
        """
        Fetch current network statistics.
        
        Returns:
            Network statistics data
        """
        try:
            await self.rate_limiter.acquire()
            
            # Get latest ledger
            ledger = self.server.ledgers().order(desc=True).limit(1).call()
            latest_ledger = ledger["_embedded"]["records"][0]
            
            # Get fee stats
            fee_stats = self.server.fee_stats().call()
            
            return {
                "latest_ledger": latest_ledger["sequence"],
                "closed_at": latest_ledger["closed_at"],
                "total_operations": latest_ledger["operation_count"],
                "base_fee": fee_stats["last_ledger_base_fee"],
                "max_fee": fee_stats["max_fee"]["max"],
            }
            
        except Exception as e:
            logger.error(f"Error fetching network stats: {e}")
            return {}
    
    async def stream_transactions(
        self,
        account_id: Optional[str] = None,
        cursor: str = "now"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream transactions in real-time.
        
        Args:
            account_id: Optional account ID to filter transactions
            cursor: Starting cursor for streaming
            
        Yields:
            Transaction data as it arrives
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.horizon_url}/transactions"
            params = {"cursor": cursor}
            
            if account_id:
                url = f"{self.horizon_url}/accounts/{account_id}/transactions"
            
            async with session.get(url, params=params) as response:
                async for line in response.content:
                    if line.startswith(b"data: "):
                        try:
                            import json
                            data = json.loads(line[6:])
                            yield self._process_transaction_data(data)
                        except json.JSONDecodeError:
                            continue
    
    def _process_account_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw account data from API."""
        return {
            "account_id": raw_data["account_id"],
            "sequence": raw_data["sequence"],
            "balance_xlm": Decimal(next(
                (b["balance"] for b in raw_data["balances"] if b["asset_type"] == "native"),
                "0"
            )),
            "num_subentries": raw_data.get("num_subentries", 0),
            "flags": raw_data.get("flags", {}).get("auth_required", False),
            "thresholds": raw_data.get("thresholds", {}),
            "last_modified_ledger": raw_data.get("last_modified_ledger"),
            "created_at": datetime.utcnow(),
        }
    
    def _process_transaction_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw transaction data from API."""
        return {
            "transaction_hash": raw_data["hash"],
            "ledger_sequence": raw_data["ledger"],
            "created_at": datetime.fromisoformat(raw_data["created_at"].rstrip("Z")),
            "source_account": raw_data["source_account"],
            "fee": int(raw_data["fee_charged"]),
            "operation_count": raw_data["operation_count"],
            "successful": raw_data["successful"],
            "memo_type": raw_data.get("memo_type", "none"),
            "memo": raw_data.get("memo"),
            "paging_token": raw_data["paging_token"],
        }
    
    def _process_payment_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw payment operation data from API."""
        payment_data = {
            "id": raw_data["id"],
            "type": raw_data["type"],
            "created_at": datetime.fromisoformat(raw_data["created_at"].rstrip("Z")),
            "transaction_hash": raw_data["transaction_hash"],
            "source_account": raw_data.get("source_account", raw_data.get("from")),
        }
        
        if raw_data["type"] == "payment":
            payment_data.update({
                "from": raw_data["from"],
                "to": raw_data["to"],
                "amount": Decimal(raw_data["amount"]),
                "asset_code": raw_data.get("asset_code", "XLM"),
                "asset_issuer": raw_data.get("asset_issuer"),
            })
        elif raw_data["type"] == "create_account":
            payment_data.update({
                "from": raw_data["source_account"],
                "to": raw_data["account"],
                "amount": Decimal(raw_data["starting_balance"]),
                "asset_code": "XLM",
                "asset_issuer": None,
            })
        elif raw_data["type"] in ["path_payment_strict_send", "path_payment_strict_receive"]:
            # Path payments могут иметь разные активы для отправки и получения
            # Используем актив назначения (destination_asset)
            
            # DEBUG: посмотрим что есть в raw_data
            asset_code_result = raw_data.get("asset_code") or raw_data.get("destination_asset_code", "XLM")
            
            if not hasattr(self, '_logged_path_payment'):
                logger.info(f"DEBUG path_payment structure:")
                logger.info(f"  type: {raw_data['type']}")
                logger.info(f"  asset_code: {raw_data.get('asset_code')}")
                logger.info(f"  destination_asset_code: {raw_data.get('destination_asset_code')}")
                logger.info(f"  asset_type: {raw_data.get('asset_type')}")
                logger.info(f"  destination_asset_type: {raw_data.get('destination_asset_type')}")
                logger.info(f"  RESULT asset_code: {asset_code_result}")
                self._logged_path_payment = True
            
            payment_data.update({
                "from": raw_data.get("from") or raw_data.get("source_account"),
                "to": raw_data.get("to"),
                "amount": Decimal(raw_data.get("amount", raw_data.get("destination_amount", "0"))),
                "asset_code": asset_code_result,
                "asset_issuer": raw_data.get("asset_issuer") or raw_data.get("destination_asset_issuer"),
            })
        
        return payment_data


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_minute: Maximum API calls per minute
        """
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        async with self.lock:
            current_time = asyncio.get_event_loop().time()
            time_since_last_call = current_time - self.last_call_time
            
            if time_since_last_call < self.min_interval:
                sleep_time = self.min_interval - time_since_last_call
                await asyncio.sleep(sleep_time)
            
            self.last_call_time = asyncio.get_event_loop().time()


class StellarDataFetcher:
    """High-level data fetcher using StellarClient."""
    
    def __init__(self, client: Optional[StellarClient] = None):
        """
        Initialize data fetcher.
        
        Args:
            client: StellarClient instance (creates new if None)
        """
        self.client = client or StellarClient()
    
    async def fetch_wallet_network(
        self,
        start_wallet: str,
        depth: int = 2,
        max_wallets: int = 100,
        strategy: str = "most_active",
        asset_filter: Optional[List[str]] = None,
        tx_type_filter: Optional[List[str]] = None,
        date_from: Union[datetime, date, None] = None,
        date_to: Union[datetime, date, None] = None,
        direction_filter: Optional[List[str]] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        max_pages: int = 25  # НОВЫЙ ПАРАМЕТР
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
        wallet_activity = {}  # Track activity for each wallet
        transactions = []
        visited = set()
        
        # First pass: collect all connected wallets and their activity WITH FILTERS
        await self._collect_wallet_activity(
            start_wallet, 
            wallet_activity, 
            transactions, 
            visited, 
            depth, 
            max_wallets * 2,  # Collect more initially to filter
            asset_filter=asset_filter,
            date_from=date_from,
            date_to=date_to,
            max_pages=max_pages  # ПЕРЕДАЕМ max_pages
        )
        
        # Select top wallets based on strategy
        if strategy == "most_active":
            # Sort by activity (number of transactions)
            sorted_wallets = sorted(
                wallet_activity.items(), 
                key=lambda x: x[1]["transaction_count"], 
                reverse=True
            )
            top_wallets = [w[0] for w in sorted_wallets[:max_wallets]]
        else:
            # Use first max_wallets found (breadth-first)
            top_wallets = list(wallet_activity.keys())[:max_wallets]
        
        # Filter transactions to only include those between top wallets
        # BUT: keep all transactions with start_wallet to preserve direct connections
        logger.info(f"========== TRANSACTION FILTERING ==========")
        logger.info(f"Total transactions collected: {len(transactions)}")
        logger.info(f"Top wallets selected: {len(top_wallets)}")
        logger.info(f"Top wallet IDs: {[w[:8] + '...' for w in list(top_wallets)[:5]]}")
        
        # ПОКАЗЫВАЕМ ПРИМЕРЫ ТРАНЗАКЦИЙ ДО ФИЛЬТРАЦИИ
        if transactions:
            logger.info(f"📋 SAMPLE TRANSACTIONS BEFORE FILTERING (first 5):")
            for i, tx in enumerate(transactions[:5]):
                logger.info(f"  TX {i+1}: from={tx.get('from', 'N/A')[:8]}... to={tx.get('to', 'N/A')[:8]}... "
                          f"asset={tx.get('asset_code', 'XLM')} amount={tx.get('amount')} type={tx.get('type')}")
        
        # Проверяем сколько from/to есть в top_wallets
        from_in_top = sum(1 for tx in transactions if tx.get("from") in top_wallets)
        to_in_top = sum(1 for tx in transactions if tx.get("to") in top_wallets)
        both_in_top = sum(1 for tx in transactions if tx.get("from") in top_wallets and tx.get("to") in top_wallets)
        logger.info(f"Transactions with FROM in top_wallets: {from_in_top}")
        logger.info(f"Transactions with TO in top_wallets: {to_in_top}")
        logger.info(f"Transactions with BOTH in top_wallets: {both_in_top}")
        
        # ИСПРАВЛЕНИЕ: Сохраняем ЛЮБЫЕ транзакции где хотя бы один кошелек в top_wallets
        # Это предотвратит потерю информации о связях
        filtered_transactions = [
            tx for tx in transactions
            if tx.get("from") in top_wallets or tx.get("to") in top_wallets
        ]
        logger.info(f"After filtering (ANY wallet in top_wallets): {len(filtered_transactions)} transactions")
        
        # Также собираем ВСЕ кошельки из финальных транзакций для графа
        all_wallet_ids_in_final = set()
        for tx in filtered_transactions:
            if tx.get("from"):
                all_wallet_ids_in_final.add(tx.get("from"))
            if tx.get("to"):
                all_wallet_ids_in_final.add(tx.get("to"))
        logger.info(f"Total unique wallets in filtered transactions: {len(all_wallet_ids_in_final)}")
        
        # Apply additional filters if specified
        if asset_filter and "All" not in asset_filter:
            before_count = len(filtered_transactions)
            filtered_transactions = [
                tx for tx in filtered_transactions
                if tx.get("asset_code", "XLM") in asset_filter
            ]
            logger.info(f"After asset filter ({asset_filter}): {len(filtered_transactions)} (removed {before_count - len(filtered_transactions)})")
        
        if tx_type_filter and "All" not in tx_type_filter:
            before_count = len(filtered_transactions)
            filtered_transactions = [
                tx for tx in filtered_transactions
                if tx.get("type") in tx_type_filter
            ]
            logger.info(f"After tx_type filter ({tx_type_filter}): {len(filtered_transactions)} (removed {before_count - len(filtered_transactions)})")
        
        if date_from or date_to:
            from datetime import datetime
            before_count = len(filtered_transactions)
            filtered_by_date = []
            for tx in filtered_transactions:
                tx_date_str = tx.get("created_at")
                if tx_date_str:
                    try:
                        # Parse ISO format date
                        tx_date = datetime.fromisoformat(tx_date_str.replace('Z', '+00:00'))
                        
                        # Check date range
                        if date_from and tx_date.date() < date_from:
                            continue
                        if date_to and tx_date.date() > date_to:
                            continue
                        
                        filtered_by_date.append(tx)
                    except:
                        # If date parsing fails, include the transaction
                        filtered_by_date.append(tx)
            filtered_transactions = filtered_by_date
            logger.info(f"After date filter ({date_from} to {date_to}): {len(filtered_transactions)} (removed {before_count - len(filtered_transactions)})")
        
        # Filter by direction (Sent/Received) relative to start_wallet
        if direction_filter and "All" not in direction_filter:
            before_count = len(filtered_transactions)
            filtered_by_direction = []
            for tx in filtered_transactions:
                tx_from = tx.get("from")
                tx_to = tx.get("to")
                
                # Check if transaction matches direction filter
                is_sent = (tx_from == start_wallet)
                is_received = (tx_to == start_wallet)
                
                include_tx = False
                if "Sent" in direction_filter and is_sent:
                    include_tx = True
                if "Received" in direction_filter and is_received:
                    include_tx = True
                
                if include_tx:
                    filtered_by_direction.append(tx)
            
            filtered_transactions = filtered_by_direction
            logger.info(f"After direction filter ({direction_filter}): {len(filtered_transactions)} (removed {before_count - len(filtered_transactions)})")
        
        # Filter by amount (-1.0 означает "не задано")
        if (min_amount is not None and min_amount >= 0) or (max_amount is not None and max_amount >= 0):
            before_count = len(filtered_transactions)
            filtered_by_amount = []
            for tx in filtered_transactions:
                try:
                    amount = float(tx.get("amount", 0))
                    
                    # Check amount range (игнорируем -1.0)
                    if min_amount is not None and min_amount >= 0 and amount < min_amount:
                        continue
                    if max_amount is not None and max_amount >= 0 and amount > max_amount:
                        continue
                    
                    filtered_by_amount.append(tx)
                except (ValueError, TypeError):
                    # If amount parsing fails, exclude the transaction
                    pass
            
            filtered_transactions = filtered_by_amount
            logger.info(f"After amount filter (min: {min_amount}, max: {max_amount}): {len(filtered_transactions)} (removed {before_count - len(filtered_transactions)})")
        
        logger.info(f"========== FINAL RESULT: {len(filtered_transactions)} transactions ==========")
        
        # Собираем статистику по фильтрации для диагностики
        filtering_stats = {
            "initial_transactions": len(transactions),
            "after_top_wallets_filter": len([
                tx for tx in transactions
                if tx.get("from") in top_wallets or tx.get("to") in top_wallets
            ]),
            "final_transactions": len(filtered_transactions),
            "transactions_lost": len(transactions) - len(filtered_transactions),
        }
        
        logger.info(f"📊 FILTERING STATISTICS:")
        logger.info(f"  Initial collected: {filtering_stats['initial_transactions']}")
        logger.info(f"  After top_wallets: {filtering_stats['after_top_wallets_filter']}")
        logger.info(f"  Final (after all filters): {filtering_stats['final_transactions']}")
        logger.info(f"  Total lost: {filtering_stats['transactions_lost']} ({filtering_stats['transactions_lost']/filtering_stats['initial_transactions']*100:.1f}%)")
        
        # Собираем все уникальные кошельки из финальных транзакций
        all_wallet_ids = set(top_wallets)
        for tx in filtered_transactions:
            if tx.get("from"):
                all_wallet_ids.add(tx.get("from"))
            if tx.get("to"):
                all_wallet_ids.add(tx.get("to"))
        
        logger.info(f"Total unique wallets in final data: {len(all_wallet_ids)} (top_wallets: {len(top_wallets)})")
        
        # Fetch detailed account data for all wallets
        wallet_details = {}
        wallets_not_found = []
        
        for wallet_id in all_wallet_ids:
            details = await self.client.get_account(wallet_id)
            if details:
                # Add activity metrics if available
                if wallet_id in wallet_activity:
                    details["transaction_count"] = wallet_activity[wallet_id]["transaction_count"]
                    details["total_volume"] = wallet_activity[wallet_id]["total_volume"]
                    details["counterparties"] = len(wallet_activity[wallet_id]["counterparties"])
                else:
                    # Default values for wallets not in original top list
                    details["transaction_count"] = 0
                    details["total_volume"] = 0
                    details["counterparties"] = 0
                wallet_details[wallet_id] = details
            else:
                # Wallet not found - but it appears in transactions!
                # Create placeholder data so it still appears on graph
                wallets_not_found.append(wallet_id)
                wallet_details[wallet_id] = {
                    "id": wallet_id,
                    "balance_xlm": 0.0,
                    "transaction_count": 0,
                    "total_volume": 0.0,
                    "counterparties": 0,
                    "account_not_found": True  # Flag for UI
                }
                logger.debug(f"Wallet {wallet_id[:12]}... not found but appears in transactions - added as placeholder")
        
        if wallets_not_found:
            logger.info(f"📊 {len(wallets_not_found)} wallets not found via get_account but appear in transactions (added as placeholders)")
        
        logger.info(f"✅ Final wallet_details: {len(wallet_details)} wallets (including {len(wallets_not_found)} placeholders)")
        
        return {
            "wallets": wallet_details,
            "transactions": filtered_transactions,
            "stats": {
                "total_wallets": len(wallet_details),
                "total_transactions": len(filtered_transactions),
                "depth_explored": depth,
                "wallets_discovered": len(wallet_activity),
                "strategy": strategy,
                "filtering_stats": filtering_stats,  # ← NEW: Добавили статистику фильтрации
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
        max_pages: int = 25  # НОВЫЙ ПАРАМЕТР
    ):
        """
        Collect wallet activity data recursively WITH FILTERS and PAGINATION.
        
        Gets ALL transactions for the specified period and asset!
        """
        if current_depth >= max_depth or len(wallet_activity) >= max_collect:
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
                
                payments = await self.client.get_all_payments_filtered(
                    account_id=wallet_id,
                    asset_code=asset_code,
                    date_from=date_from,
                    date_to=date_to,
                    max_pages=max_pages  # Используем переданный параметр
                )
                
                logger.info(f"Got {len(payments)} payments for asset {asset_code or 'ALL'}")
                all_payments.extend(payments)
            
            logger.info(f"Total collected {len(all_payments)} payments for {wallet_id[:8]}")
            
            # ДЕТАЛЬНОЕ логирование первых 3 транзакций
            if all_payments:
                logger.info(f"📋 SAMPLE TRANSACTIONS (first 3):")
                for i, p in enumerate(all_payments[:3]):
                    logger.info(f"  TX {i+1}: from={p.get('from', 'N/A')[:8]} to={p.get('to', 'N/A')[:8]} "
                              f"asset={p.get('asset_code', 'XLM')} amount={p.get('amount')} date={p.get('created_at')}")
            
            logger.info(f"==========================================")
            
            tx_added = 0
            for payment in all_payments:
                if "from" in payment and "to" in payment:
                    from_wallet = payment["from"]
                    to_wallet = payment["to"]
                    amount = float(payment.get("amount", 0))
                    
                    # Track transaction
                    transactions.append(payment)
                    tx_added += 1
                    
                    # Update activity metrics for both wallets
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
                    if current_depth + 1 < max_depth:
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
                                    max_pages=max_pages  # ПЕРЕДАЕМ max_pages
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
        # This would ideally query an indexed database or use Stellar's 
        # trade aggregation endpoints for efficiency
        # For now, we'll use a sampling approach
        
        logger.info(f"Fetching top {limit} active wallets...")
        
        # Start with known active addresses (exchanges, anchors)
        seed_wallets = [
            # These would be real known active addresses
            "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN7",  # Example
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
            
            # Merge results
            for wallet_id, details in data["wallets"].items():
                if wallet_id not in wallet_activity:
                    wallet_activity[wallet_id] = details
            
            all_transactions.extend(data["transactions"])
        
        # Sort by activity and return top
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
            }
        }
