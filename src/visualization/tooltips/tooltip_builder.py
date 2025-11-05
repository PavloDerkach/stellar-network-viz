"""Tooltip builder for graph visualization."""

from typing import Dict, List, Optional, Any
import requests
import networkx as nx


class TooltipBuilder:
    """Handles tooltip generation for graph nodes."""
    
    def __init__(self):
        """Initialize tooltip builder."""
        self.xlm_to_usdc_rate = None
        self.rate_cache_time = 0
    
    def create_node_tooltips(
        self,
        graph: nx.Graph,
        start_wallet: Optional[str] = None,
        selected_asset: str = "XLM",
        transactions: Optional[List[Dict[str, Any]]] = None,
        data_completeness: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Create tooltips for all nodes in the graph.
        
        Args:
            graph: NetworkX graph
            start_wallet: Starting wallet for context
            selected_asset: Currently selected asset filter
            transactions: List of all transactions (for dynamic calculation)
            data_completeness: Data completeness information
            
        Returns:
            Dictionary mapping node ID to tooltip HTML
        """
        tooltips = {}
        
        for node in graph.nodes():
            tooltip = self._create_single_tooltip(
                node,
                graph,
                start_wallet,
                selected_asset,
                transactions,
                data_completeness
            )
            tooltips[node] = tooltip
        
        return tooltips
    
    def _create_single_tooltip(
        self,
        node: str,
        graph: nx.Graph,
        start_wallet: Optional[str] = None,
        selected_asset: str = "XLM",
        transactions: Optional[List[Dict[str, Any]]] = None,
        data_completeness: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create tooltip for a single node."""
        lines = []
        
        # Header with node type
        if node == start_wallet:
            lines.append("🎯 START WALLET")
        else:
            lines.append("📊 WALLET")
        
        # Wallet address
        lines.append("🏦 Wallet Address:")
        lines.append(f"{node}")
        lines.append("💡 Click to open details sidebar")
        lines.append("━" * 20)
        
        # Balance with conversion
        balance_xlm = graph.nodes[node].get("balance_xlm", 0)
        balance_line = self._format_balance(balance_xlm, selected_asset)
        lines.append(f"💰 Balance: {balance_line}")
        lines.append("━" * 20)
        
        # Activity metrics (dynamic calculation)
        if transactions and selected_asset != "All":
            activity = self._calculate_activity(
                node, 
                transactions, 
                selected_asset,
                start_wallet
            )
            
            lines.append(f"📊 Activity in {selected_asset} for selected period:")
            
            if start_wallet:
                lines.append(f"  • Total transactions in {selected_asset} with {self._truncate(start_wallet)}: {activity['connections']}")
            else:
                lines.append(f"  • Total transactions in {selected_asset}: {activity['total_tx']}")
            
            lines.append(f"  • Sent (Outgoing): {activity['sent']:.2f} {selected_asset}")
            lines.append(f"  • Received (Incoming): {activity['received']:.2f} {selected_asset}")
            
            net_flow = activity['received'] - activity['sent']
            flow_icon = "📈" if net_flow > 0 else "📉" if net_flow < 0 else "➖"
            lines.append(f"  • Net Flow: {flow_icon} {abs(net_flow):.2f} {selected_asset}")
        else:
            # Fallback to static data if no transactions provided
            lines.append("📊 Network Activity:")
            degree = graph.degree(node)
            lines.append(f"  • Connected wallets: {degree}")
            
            if graph.nodes[node].get("transaction_count"):
                tx_count = graph.nodes[node].get("transaction_count", 0)
                lines.append(f"  • Total transactions: {tx_count}")
        
        lines.append("━" * 20)
        
        # Data completeness check
        if data_completeness:
            completeness_line = self._format_completeness(node, data_completeness)
            lines.append(f"📦 Data: {completeness_line}")
        
        lines.append("Adjust filters to see different flows!")
        
        return "<br>".join(lines)
    
    def _calculate_activity(
        self,
        node: str,
        transactions: List[Dict[str, Any]],
        selected_asset: str,
        start_wallet: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate activity metrics for a node dynamically.
        
        This is the FIX for the 0.00 bug - calculate from filtered transactions!
        """
        # Filter transactions for this node and asset
        node_txs = []
        for tx in transactions:
            if tx.get('asset_code', 'XLM') == selected_asset:
                if tx.get('from') == node or tx.get('to') == node:
                    node_txs.append(tx)
        
        # Calculate metrics
        total_sent = 0
        total_received = 0
        connections_with_start = 0
        
        for tx in node_txs:
            amount = tx.get('amount', 0)
            # Convert Decimal to float if needed
            if hasattr(amount, 'to_eng_string'):  # It's a Decimal
                amount = float(amount)
            
            if tx.get('from') == node:
                total_sent += amount
                if tx.get('to') == start_wallet:
                    connections_with_start += 1
            
            if tx.get('to') == node:
                total_received += amount
                if tx.get('from') == start_wallet:
                    connections_with_start += 1
        
        return {
            'sent': total_sent,
            'received': total_received,
            'connections': connections_with_start,
            'total_tx': len(node_txs)
        }
    
    def _format_balance(self, balance_xlm: float, selected_asset: str) -> str:
        """Format balance with currency conversion."""
        # Convert Decimal to float if needed
        if hasattr(balance_xlm, 'to_eng_string'):  # It's a Decimal
            balance_xlm = float(balance_xlm)
            
        if selected_asset == "USDC":
            # Convert XLM to USDC
            rate = self._get_xlm_to_usdc_rate()
            balance_usdc = balance_xlm * rate
            return f"{balance_usdc:.2f} USDC (≈{balance_xlm:.4f} XLM)"
        else:
            return f"{balance_xlm:.4f} XLM"
    
    def _format_completeness(
        self, 
        node: str,
        data_completeness: Dict[str, Any]
    ) -> str:
        """Format data completeness information."""
        if not data_completeness:
            return "Unknown"
        
        # Check if this wallet's data is truncated
        truncated_wallets = data_completeness.get('truncated_wallets', [])
        wallets_check = data_completeness.get('wallets_check', {})
        
        if node in truncated_wallets or node in wallets_check:
            wallet_info = wallets_check.get(node, {})
            pages = wallet_info.get('pages_fetched', 0)
            has_more = wallet_info.get('has_more', False)
            
            if has_more:
                return f"⚠️ Partial ({pages} pages, more available)"
            else:
                return f"✅ Complete ({pages} pages)"
        
        # General completeness
        if data_completeness.get('all_data_loaded'):
            total_pages = data_completeness.get('total_pages_fetched', 0)
            return f"✅ Complete ({total_pages} pages)"
        else:
            return "⚠️ Partial (limited by settings)"
    
    def _get_xlm_to_usdc_rate(self) -> float:
        """Get XLM to USDC conversion rate with caching."""
        import time
        
        # Cache for 5 minutes
        current_time = time.time()
        if self.xlm_to_usdc_rate and (current_time - self.rate_cache_time) < 300:
            return self.xlm_to_usdc_rate
        
        try:
            # Try to get rate from API
            response = requests.get(
                "https://api.binance.com/api/v3/ticker/price?symbol=XLMUSDC",
                timeout=2
            )
            if response.status_code == 200:
                rate = float(response.json()['price'])
                self.xlm_to_usdc_rate = rate
                self.rate_cache_time = current_time
                return rate
        except:
            pass
        
        # Fallback rate
        if not self.xlm_to_usdc_rate:
            self.xlm_to_usdc_rate = 0.10
        
        return self.xlm_to_usdc_rate
    
    def _truncate(self, address: str, length: int = 8) -> str:
        """Truncate address for display."""
        if len(address) <= length * 2:
            return address
        return f"{address[:length]}...{address[-4:]}"
