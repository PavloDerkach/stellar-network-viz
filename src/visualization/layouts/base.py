"""Base class for graph layout algorithms."""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional
import networkx as nx


class BaseLayout(ABC):
    """Abstract base class for graph layout algorithms."""
    
    def __init__(self, seed: int = 42):
        """
        Initialize layout algorithm.
        
        Args:
            seed: Random seed for reproducible layouts
        """
        self.seed = seed
        self.pos_cache = {}
    
    @abstractmethod
    def calculate(
        self, 
        graph: nx.Graph,
        **kwargs
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate node positions for the graph.
        
        Args:
            graph: NetworkX graph
            **kwargs: Algorithm-specific parameters
            
        Returns:
            Dictionary mapping node IDs to (x, y) positions
        """
        pass
    
    def get_cache_key(self, graph: nx.Graph, **kwargs) -> str:
        """Generate cache key for layout."""
        nodes = sorted(graph.nodes())
        edges = sorted(graph.edges())
        params = sorted(kwargs.items())
        return f"{nodes}_{edges}_{params}"
    
    def get_cached_positions(
        self, 
        graph: nx.Graph,
        **kwargs
    ) -> Optional[Dict[str, Tuple[float, float]]]:
        """Get cached positions if available."""
        key = self.get_cache_key(graph, **kwargs)
        return self.pos_cache.get(key)
    
    def cache_positions(
        self,
        graph: nx.Graph,
        positions: Dict[str, Tuple[float, float]],
        **kwargs
    ):
        """Cache calculated positions."""
        key = self.get_cache_key(graph, **kwargs)
        self.pos_cache[key] = positions
    
    def clear_cache(self):
        """Clear position cache."""
        self.pos_cache.clear()
