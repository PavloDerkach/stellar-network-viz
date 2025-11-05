"""Spring layout algorithm for graph visualization."""

from typing import Dict, Tuple, Optional
import numpy as np
import networkx as nx
from .base import BaseLayout


class SpringLayout(BaseLayout):
    """Spring-force directed layout algorithm."""
    
    # Layout parameters
    DEFAULT_ITERATIONS = 200
    DEFAULT_SCALE = 8.0
    START_WALLET_MULTIPLIER = 3.0
    
    def calculate(
        self, 
        graph: nx.Graph,
        center_node: Optional[str] = None,
        node_size: int = 30,
        **kwargs
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate spring layout positions with custom distance logic.
        
        RULES:
        - 1 transaction = 100% distance (EDGE of graph)  
        - More transactions = PROPORTIONALLY CLOSER to center
        - Formula: distance = max_distance * (1 / tx_count)
        
        Args:
            graph: NetworkX graph
            center_node: Node to place at center
            node_size: Size of nodes in pixels
            **kwargs: Additional layout parameters
            
        Returns:
            Dictionary of node positions
        """
        # Check cache first
        cached = self.get_cached_positions(graph, center_node=center_node, **kwargs)
        if cached:
            return cached
            
        if center_node:
            pos = self._calculate_centered_layout(graph, center_node, node_size)
        else:
            pos = self._calculate_standard_layout(graph, **kwargs)
        
        # Cache the result
        self.cache_positions(graph, pos, center_node=center_node, **kwargs)
        return pos
    
    def _calculate_standard_layout(
        self,
        graph: nx.Graph,
        **kwargs
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate standard spring layout."""
        n_nodes = len(graph.nodes())
        
        if n_nodes == 0:
            return {}
        
        # Optimal k value for node separation
        optimal_k = 3.0 / np.sqrt(n_nodes) if n_nodes > 1 else 1.0
        
        return nx.spring_layout(
            graph,
            k=optimal_k,
            iterations=kwargs.get('iterations', self.DEFAULT_ITERATIONS),
            scale=kwargs.get('scale', self.DEFAULT_SCALE),
            seed=self.seed
        )
    
    def _calculate_centered_layout(
        self,
        graph: nx.Graph,
        center_node: str,
        node_size: int
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate spring layout with a specific node at center.
        
        Places center node at (0,0) and arranges other nodes based on
        transaction count - more transactions = closer to center.
        """
        pos = {}
        
        # Center node at origin
        pos[center_node] = (0.0, 0.0)
        
        # Calculate radii for collision avoidance
        center_radius = (node_size * self.START_WALLET_MULTIPLIER) / 50.0
        regular_radius = node_size / 50.0
        
        # INCREASED minimum separations to avoid overlap
        min_node_separation = 8 * regular_radius  # 8 radii between centers (was 5)
        min_distance_from_center = 10 * (center_radius * 2)  # 10 diameters from center (was 6)
        max_distance = 12.0  # Maximum distance for nodes with 1 transaction (was 8)
        
        # Collect transaction counts for each neighbor
        neighbors = []
        tx_counts = {}
        
        for node in graph.nodes():
            if node == center_node:
                continue
                
            # Count transactions with center node
            tx_count = 0
            if graph.has_edge(center_node, node):
                edge_data = graph[center_node][node]
                tx_count = edge_data.get('transaction_count', 1)
            
            if tx_count > 0:
                tx_counts[node] = tx_count
                neighbors.append((node, tx_count))
        
        # Sort by transaction count (most transactions first)
        neighbors.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate max transaction count for normalization
        max_tx = max(tx_counts.values()) if tx_counts else 1
        
        # Position nodes using golden angle spiral for better distribution
        golden_angle = np.pi * (3.0 - np.sqrt(5.0))  # ~137.5 degrees
        
        placed_positions = []
        
        for i, (node, tx_count) in enumerate(neighbors):
            # Calculate distance based on transaction count
            # More transactions = closer to center
            normalized_tx = tx_count / max_tx
            
            # Inverse relationship: 1 tx = max_distance, max_tx = min_distance
            if tx_count == 1:
                base_distance = max_distance
            else:
                # Logarithmic scale for better distribution
                distance_factor = 1.0 - (np.log(tx_count) / np.log(max_tx + 1))
                base_distance = min_distance_from_center + (
                    (max_distance - min_distance_from_center) * distance_factor
                )
            
            # Try to place node with collision avoidance
            placed = False
            attempts = 0
            max_attempts = 36  # Try 36 different angles
            
            while not placed and attempts < max_attempts:
                # Calculate angle using golden angle spiral
                angle = i * golden_angle + (attempts * np.pi / 18)
                
                # Calculate position
                x = base_distance * np.cos(angle)
                y = base_distance * np.sin(angle)
                
                # Check for collisions with already placed nodes
                collision = False
                for other_pos in placed_positions:
                    dist = np.sqrt((x - other_pos[0])**2 + (y - other_pos[1])**2)
                    if dist < min_node_separation:
                        collision = True
                        break
                
                if not collision:
                    pos[node] = (x, y)
                    placed_positions.append((x, y))
                    placed = True
                else:
                    attempts += 1
                    # Slightly increase distance on collision
                    base_distance *= 1.05
            
            # Fallback if no position found
            if not placed:
                angle = i * golden_angle
                x = (max_distance * 1.2) * np.cos(angle)
                y = (max_distance * 1.2) * np.sin(angle)
                pos[node] = (x, y)
        
        # Add any remaining unconnected nodes at the periphery
        unconnected = [n for n in graph.nodes() if n not in pos]
        if unconnected:
            angle_step = 2 * np.pi / len(unconnected) if unconnected else 0
            for i, node in enumerate(unconnected):
                angle = i * angle_step
                x = max_distance * 1.5 * np.cos(angle)
                y = max_distance * 1.5 * np.sin(angle)
                pos[node] = (x, y)
        
        return pos
