"""Unified graph builder with strategy pattern."""
from typing import Dict, Any, List, Optional, Protocol
import networkx as nx
import logging
import sys
from pathlib import Path

# FIX PATHS
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.visualization.graph_builder_pyvis import PyVisGraphBuilder

logger = logging.getLogger(__name__)


class GraphBuilderProtocol(Protocol):
    """Protocol for graph builders."""
    
    def build_graph(
        self,
        wallets: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        directed: bool = True
    ) -> nx.Graph:
        ...
    
    def create_interactive_figure(
        self,
        graph: nx.Graph,
        **kwargs
    ) -> Any:
        ...


class UnifiedGraphBuilder:
    """Unified graph builder using strategy pattern."""
    
    def __init__(self, backend: str = "pyvis"):
        """Initialize graph builder."""
        self.backend = backend
        self._builder = self._get_builder(backend)
    
    def _get_builder(self, backend: str) -> GraphBuilderProtocol:
        """Get appropriate builder based on backend."""
        if backend == "pyvis":
            return PyVisGraphBuilder()
        else:
            logger.warning(f"Unknown backend {backend}, using PyVis")
            return PyVisGraphBuilder()
    
    def build_graph(
        self,
        wallets: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        directed: bool = True
    ) -> nx.Graph:
        """Build NetworkX graph."""
        return self._builder.build_graph(wallets, transactions, directed)
    
    def create_visualization(
        self,
        graph: nx.Graph,
        **kwargs
    ) -> Any:
        """Create interactive visualization."""
        return self._builder.create_interactive_figure(graph, **kwargs)
    
    def create_filtered_graph(
        self,
        data: Dict[str, Any],
        min_tx_count: int = 0,
        **kwargs
    ) -> Optional[str]:
        """Create filtered graph from data."""
        
        if not data or not data.get("wallets") or not data.get("transactions"):
            return None
        
        if min_tx_count > 0:
            edge_counts = {}
            for tx in data["transactions"]:
                edge = (tx.get("from"), tx.get("to"))
                if edge[0] and edge[1]:
                    edge_counts[edge] = edge_counts.get(edge, 0) + 1
            
            filtered_txs = [
                tx for tx in data["transactions"]
                if edge_counts.get((tx.get("from"), tx.get("to")), 0) >= min_tx_count
            ]
            logger.info(f"Filtered {len(data['transactions'])} -> {len(filtered_txs)} transactions")
        else:
            filtered_txs = data["transactions"]
        
        G = self.build_graph(data["wallets"], filtered_txs, directed=True)
        
        if len(G.nodes()) == 0:
            return None
        
        logger.info(f"Built graph with {len(G.nodes())} nodes and {len(G.edges())} edges")
        
        return self.create_visualization(G, **kwargs)
