"""
Wallet analyzer for ranking and analyzing wallet activity.
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class WalletAnalyzer:
    """Analyze and rank wallets based on various metrics."""
    
    def __init__(self):
        """Initialize wallet analyzer."""
        self.metrics_cache = {}
    
    def calculate_wallet_metrics(
        self,
        wallets: Dict[str, Any],
        transactions: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Calculate comprehensive metrics for all wallets.
        
        Args:
            wallets: Dictionary of wallet data
            transactions: List of transaction data
            
        Returns:
            DataFrame with wallet metrics
        """
        metrics = []
        
        for wallet_id, wallet_data in wallets.items():
            # Calculate transaction metrics
            tx_metrics = self._calculate_transaction_metrics(wallet_id, transactions)
            
            # Calculate network metrics
            network_metrics = self._calculate_network_metrics(wallet_id, transactions)
            
            # Combine all metrics
            wallet_metrics = {
                "wallet_id": wallet_id,
                "wallet_short": f"{wallet_id[:8]}...{wallet_id[-6:]}",
                
                # Balance metrics
                "balance_xlm": float(wallet_data.get("balance_xlm", 0)),
                
                # Transaction metrics
                "total_transactions": tx_metrics["total"],
                "sent_transactions": tx_metrics["sent"],
                "received_transactions": tx_metrics["received"],
                "total_volume": tx_metrics["total_volume"],
                "sent_volume": tx_metrics["sent_volume"],
                "received_volume": tx_metrics["received_volume"],
                "avg_transaction_size": tx_metrics["avg_size"],
                
                # Network metrics
                "unique_counterparties": network_metrics["unique_counterparties"],
                "in_degree": network_metrics["in_degree"],
                "out_degree": network_metrics["out_degree"],
                "clustering_coefficient": network_metrics["clustering"],
                
                # Activity metrics
                "first_transaction": tx_metrics["first_tx"],
                "last_transaction": tx_metrics["last_tx"],
                "days_active": tx_metrics["days_active"],
                
                # Scoring
                "activity_score": self._calculate_activity_score(tx_metrics, network_metrics),
                "influence_score": self._calculate_influence_score(tx_metrics, network_metrics),
            }
            
            metrics.append(wallet_metrics)
        
        df = pd.DataFrame(metrics)
        
        # Calculate relative rankings
        if not df.empty:
            df["volume_rank"] = df["total_volume"].rank(ascending=False, method="min")
            df["transaction_rank"] = df["total_transactions"].rank(ascending=False, method="min")
            df["counterparty_rank"] = df["unique_counterparties"].rank(ascending=False, method="min")
            df["activity_rank"] = df["activity_score"].rank(ascending=False, method="min")
            
            # Overall rank (weighted average)
            df["overall_rank"] = (
                df["volume_rank"] * 0.3 +
                df["transaction_rank"] * 0.3 +
                df["counterparty_rank"] * 0.2 +
                df["activity_rank"] * 0.2
            ).rank(method="min")
        
        return df
    
    def rank_wallets(
        self,
        wallets: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        by: str = "activity",
        top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank wallets by specified metric.
        
        Args:
            wallets: Dictionary of wallet data
            transactions: List of transaction data
            by: Metric to rank by (activity, volume, transactions, influence)
            top_n: Return only top N wallets
            
        Returns:
            Ranked list of wallet data
        """
        df = self.calculate_wallet_metrics(wallets, transactions)
        
        # Sort by specified metric
        if by == "activity":
            df = df.sort_values("activity_score", ascending=False)
        elif by == "volume":
            df = df.sort_values("total_volume", ascending=False)
        elif by == "transactions":
            df = df.sort_values("total_transactions", ascending=False)
        elif by == "influence":
            df = df.sort_values("influence_score", ascending=False)
        elif by == "balance":
            df = df.sort_values("balance_xlm", ascending=False)
        else:
            df = df.sort_values("overall_rank")
        
        # Limit to top N if specified
        if top_n:
            df = df.head(top_n)
        
        return df.to_dict("records")
    
    def identify_wallet_types(
        self,
        wallets: Dict[str, Any],
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Identify wallet types based on behavior patterns.
        
        Args:
            wallets: Dictionary of wallet data
            transactions: List of transaction data
            
        Returns:
            Dictionary mapping wallet_id to type
        """
        wallet_types = {}
        df = self.calculate_wallet_metrics(wallets, transactions)
        
        for _, row in df.iterrows():
            wallet_id = row["wallet_id"]
            
            # High volume, many counterparties -> likely exchange
            if (row["total_volume"] > df["total_volume"].quantile(0.9) and
                row["unique_counterparties"] > df["unique_counterparties"].quantile(0.9)):
                wallet_types[wallet_id] = "exchange"
            
            # High balance, few transactions -> likely holder
            elif (row["balance_xlm"] > df["balance_xlm"].quantile(0.8) and
                  row["total_transactions"] < df["total_transactions"].quantile(0.3)):
                wallet_types[wallet_id] = "holder"
            
            # Many small transactions -> likely bot/trader
            elif (row["total_transactions"] > df["total_transactions"].quantile(0.8) and
                  row["avg_transaction_size"] < df["avg_transaction_size"].quantile(0.3)):
                wallet_types[wallet_id] = "bot_trader"
            
            # High out-degree, low in-degree -> likely distributor
            elif row["out_degree"] > row["in_degree"] * 2:
                wallet_types[wallet_id] = "distributor"
            
            # High in-degree, low out-degree -> likely collector
            elif row["in_degree"] > row["out_degree"] * 2:
                wallet_types[wallet_id] = "collector"
            
            else:
                wallet_types[wallet_id] = "regular"
        
        return wallet_types
    
    def find_connected_clusters(
        self,
        transactions: List[Dict[str, Any]],
        min_cluster_size: int = 3
    ) -> List[List[str]]:
        """
        Find clusters of highly connected wallets.
        
        Args:
            transactions: List of transaction data
            min_cluster_size: Minimum size for a cluster
            
        Returns:
            List of wallet clusters
        """
        # Build adjacency list
        connections = defaultdict(set)
        
        for tx in transactions:
            if "from" in tx and "to" in tx:
                connections[tx["from"]].add(tx["to"])
                connections[tx["to"]].add(tx["from"])
        
        # Find connected components
        visited = set()
        clusters = []
        
        for wallet in connections:
            if wallet not in visited:
                cluster = self._dfs_cluster(wallet, connections, visited)
                if len(cluster) >= min_cluster_size:
                    clusters.append(list(cluster))
        
        # Sort clusters by size
        clusters.sort(key=len, reverse=True)
        
        return clusters
    
    def calculate_centrality_metrics(
        self,
        wallets: Dict[str, Any],
        transactions: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Calculate centrality metrics for network analysis.
        
        Args:
            wallets: Dictionary of wallet data
            transactions: List of transaction data
            
        Returns:
            DataFrame with centrality metrics
        """
        import networkx as nx
        
        # Build network graph
        G = nx.DiGraph()
        
        for wallet_id in wallets:
            G.add_node(wallet_id)
        
        for tx in transactions:
            if "from" in tx and "to" in tx:
                if tx["from"] in G and tx["to"] in G:
                    weight = float(tx.get("amount", 1))
                    if G.has_edge(tx["from"], tx["to"]):
                        G[tx["from"]][tx["to"]]["weight"] += weight
                    else:
                        G.add_edge(tx["from"], tx["to"], weight=weight)
        
        # Calculate centrality metrics
        metrics = []
        
        degree_centrality = nx.degree_centrality(G)
        betweenness = nx.betweenness_centrality(G) if G.number_of_nodes() > 2 else {}
        closeness = nx.closeness_centrality(G) if G.number_of_nodes() > 1 else {}
        
        try:
            pagerank = nx.pagerank(G, max_iter=100)
        except:
            pagerank = {}
        
        for wallet_id in wallets:
            metrics.append({
                "wallet_id": wallet_id,
                "degree_centrality": degree_centrality.get(wallet_id, 0),
                "betweenness_centrality": betweenness.get(wallet_id, 0),
                "closeness_centrality": closeness.get(wallet_id, 0),
                "pagerank": pagerank.get(wallet_id, 0),
            })
        
        return pd.DataFrame(metrics)
    
    def _calculate_transaction_metrics(
        self,
        wallet_id: str,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate transaction-based metrics for a wallet."""
        sent_txs = []
        received_txs = []
        
        for tx in transactions:
            if tx.get("from") == wallet_id:
                sent_txs.append(tx)
            if tx.get("to") == wallet_id:
                received_txs.append(tx)
        
        all_txs = sent_txs + received_txs
        
        # Calculate volumes
        sent_volume = sum(float(tx.get("amount", 0)) for tx in sent_txs)
        received_volume = sum(float(tx.get("amount", 0)) for tx in received_txs)
        total_volume = sent_volume + received_volume
        
        # Calculate dates
        dates = [tx.get("created_at") for tx in all_txs if tx.get("created_at")]
        first_tx = min(dates) if dates else None
        last_tx = max(dates) if dates else None
        
        days_active = (last_tx - first_tx).days if first_tx and last_tx else 0
        
        return {
            "total": len(all_txs),
            "sent": len(sent_txs),
            "received": len(received_txs),
            "sent_volume": sent_volume,
            "received_volume": received_volume,
            "total_volume": total_volume,
            "avg_size": total_volume / len(all_txs) if all_txs else 0,
            "first_tx": first_tx,
            "last_tx": last_tx,
            "days_active": days_active,
        }
    
    def _calculate_network_metrics(
        self,
        wallet_id: str,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate network-based metrics for a wallet."""
        in_neighbors = set()
        out_neighbors = set()
        all_neighbors = set()
        
        for tx in transactions:
            if tx.get("from") == wallet_id and tx.get("to"):
                out_neighbors.add(tx["to"])
                all_neighbors.add(tx["to"])
            if tx.get("to") == wallet_id and tx.get("from"):
                in_neighbors.add(tx["from"])
                all_neighbors.add(tx["from"])
        
        # Calculate clustering coefficient (simplified)
        clustering = 0
        if len(all_neighbors) > 1:
            # Count edges between neighbors
            neighbor_edges = 0
            for tx in transactions:
                if tx.get("from") in all_neighbors and tx.get("to") in all_neighbors:
                    neighbor_edges += 1
            
            # Calculate clustering coefficient
            possible_edges = len(all_neighbors) * (len(all_neighbors) - 1)
            clustering = neighbor_edges / possible_edges if possible_edges > 0 else 0
        
        return {
            "unique_counterparties": len(all_neighbors),
            "in_degree": len(in_neighbors),
            "out_degree": len(out_neighbors),
            "clustering": clustering,
        }
    
    def _calculate_activity_score(
        self,
        tx_metrics: Dict[str, Any],
        network_metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall activity score for a wallet."""
        # Weighted combination of metrics
        score = (
            np.log1p(tx_metrics["total"]) * 0.3 +
            np.log1p(tx_metrics["total_volume"]) * 0.3 +
            np.log1p(network_metrics["unique_counterparties"]) * 0.2 +
            np.log1p(tx_metrics["days_active"]) * 0.2
        )
        
        return round(score, 2)
    
    def _calculate_influence_score(
        self,
        tx_metrics: Dict[str, Any],
        network_metrics: Dict[str, Any]
    ) -> float:
        """Calculate influence score based on network position."""
        score = (
            network_metrics["unique_counterparties"] * 0.4 +
            (network_metrics["in_degree"] + network_metrics["out_degree"]) * 0.3 +
            network_metrics["clustering"] * 100 * 0.3
        )
        
        return round(score, 2)
    
    def _dfs_cluster(
        self,
        start: str,
        connections: Dict[str, set],
        visited: set
    ) -> set:
        """DFS to find connected cluster."""
        cluster = set()
        stack = [start]
        
        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                cluster.add(node)
                stack.extend(connections[node] - visited)
        
        return cluster
