"""Additional layout algorithms for graph visualization."""

from typing import Dict, Tuple
import numpy as np
import networkx as nx
from .base import BaseLayout


class CircularLayout(BaseLayout):
    """Circular layout algorithm."""
    
    def calculate(
        self, 
        graph: nx.Graph,
        **kwargs
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate circular layout positions."""
        cached = self.get_cached_positions(graph, **kwargs)
        if cached:
            return cached
        
        pos = nx.circular_layout(graph, scale=5.0)
        
        self.cache_positions(graph, pos, **kwargs)
        return pos


class SpectralLayout(BaseLayout):
    """Spectral layout algorithm using eigenvalues."""
    
    def calculate(
        self, 
        graph: nx.Graph,
        **kwargs
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate spectral layout positions."""
        cached = self.get_cached_positions(graph, **kwargs)
        if cached:
            return cached
        
        try:
            pos = nx.spectral_layout(graph, scale=5.0)
        except:
            # Fallback to spring layout if spectral fails
            pos = nx.spring_layout(graph, scale=5.0, seed=self.seed)
        
        self.cache_positions(graph, pos, **kwargs)
        return pos


class KamadaKawaiLayout(BaseLayout):
    """Kamada-Kawai force-directed layout algorithm."""
    
    def calculate(
        self, 
        graph: nx.Graph,
        **kwargs
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate Kamada-Kawai layout positions."""
        cached = self.get_cached_positions(graph, **kwargs)
        if cached:
            return cached
        
        try:
            pos = nx.kamada_kawai_layout(graph, scale=5.0)
        except:
            # Fallback to spring layout if Kamada-Kawai fails
            pos = nx.spring_layout(graph, scale=5.0, seed=self.seed)
        
        self.cache_positions(graph, pos, **kwargs)
        return pos
