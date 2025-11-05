"""Hierarchical layout algorithm for graph visualization."""

from typing import Dict, Tuple, Optional, Set
import networkx as nx
from collections import deque
from .base import BaseLayout


class HierarchicalLayout(BaseLayout):
    """Hierarchical (tree-like) layout algorithm."""
    
    def calculate(
        self, 
        graph: nx.Graph,
        start_node: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate hierarchical layout positions.
        
        Args:
            graph: NetworkX graph
            start_node: Root node for hierarchy
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of node positions
        """
        # Check cache
        cached = self.get_cached_positions(graph, start_node=start_node, **kwargs)
        if cached:
            return cached
        
        if len(graph.nodes()) == 0:
            return {}
        
        # Select root node if not provided
        if not start_node or start_node not in graph.nodes():
            # Use node with highest degree as root
            start_node = max(graph.nodes(), key=lambda n: graph.degree(n))
        
        # Build hierarchy using BFS
        levels = self._build_hierarchy(graph, start_node)
        
        # Calculate positions
        pos = self._calculate_positions(levels)
        
        # Cache result
        self.cache_positions(graph, pos, start_node=start_node, **kwargs)
        return pos
    
    def _build_hierarchy(
        self, 
        graph: nx.Graph, 
        root: str
    ) -> Dict[int, list]:
        """
        Build hierarchy levels using BFS.
        
        Args:
            graph: NetworkX graph
            root: Root node
            
        Returns:
            Dictionary mapping level to list of nodes
        """
        levels = {0: [root]}
        visited = {root}
        queue = deque([(root, 0)])
        
        while queue:
            node, level = queue.popleft()
            
            for neighbor in graph.neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_level = level + 1
                    
                    if next_level not in levels:
                        levels[next_level] = []
                    levels[next_level].append(neighbor)
                    
                    queue.append((neighbor, next_level))
        
        # Add any disconnected nodes at the bottom
        all_nodes = set(graph.nodes())
        placed_nodes = visited
        disconnected = all_nodes - placed_nodes
        
        if disconnected:
            max_level = max(levels.keys()) if levels else 0
            levels[max_level + 1] = list(disconnected)
        
        return levels
    
    def _calculate_positions(
        self,
        levels: Dict[int, list]
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate x,y positions for nodes in hierarchy.
        
        Args:
            levels: Dictionary mapping level to nodes
            
        Returns:
            Dictionary of node positions
        """
        pos = {}
        
        if not levels:
            return pos
        
        # Calculate vertical spacing
        num_levels = len(levels)
        if num_levels == 1:
            y_spacing = 0
        else:
            y_spacing = 10.0 / (num_levels - 1)
        
        # Position nodes level by level
        for level, nodes in levels.items():
            y = 5.0 - (level * y_spacing)  # Top to bottom
            
            # Calculate horizontal spacing for this level
            num_nodes = len(nodes)
            if num_nodes == 1:
                x_positions = [0.0]
            else:
                x_spacing = 10.0 / (num_nodes - 1)
                x_positions = [-5.0 + i * x_spacing for i in range(num_nodes)]
            
            # Assign positions
            for node, x in zip(nodes, x_positions):
                pos[node] = (x, y)
        
        return pos
