"""Edge renderer for graph visualization."""

from typing import Dict, List, Optional, Tuple
import networkx as nx
import plotly.graph_objects as go


class EdgeRenderer:
    """Handles edge rendering for graph visualization."""
    
    # Visual constants
    MIN_EDGE_WIDTH = 0.5
    MAX_EDGE_WIDTH = 5.0
    DEFAULT_EDGE_COLOR = 'rgba(150, 150, 150, 0.3)'
    HIGHLIGHTED_EDGE_COLOR = 'rgba(255, 0, 0, 0.6)'
    
    def create_edge_traces(
        self,
        graph: nx.Graph,
        pos: Dict[str, Tuple[float, float]],
        highlight_node: Optional[str] = None,
        start_wallet: Optional[str] = None
    ) -> List[go.Scatter]:
        """
        Create Plotly traces for edges.
        
        Args:
            graph: NetworkX graph
            pos: Node positions
            highlight_node: Node whose edges to highlight
            start_wallet: Starting wallet for special highlighting
            
        Returns:
            List of Plotly scatter traces for edges
        """
        traces = []
        
        # Group edges by visual properties for efficient rendering
        edge_groups = self._group_edges(graph, highlight_node, start_wallet)
        
        for group_props, edges in edge_groups.items():
            trace = self._create_edge_group_trace(edges, pos, group_props)
            if trace:
                traces.append(trace)
        
        return traces
    
    def _group_edges(
        self,
        graph: nx.Graph,
        highlight_node: Optional[str] = None,
        start_wallet: Optional[str] = None
    ) -> Dict[tuple, List[tuple]]:
        """
        Group edges by visual properties for batch rendering.
        
        Returns:
            Dictionary mapping (color, width, style) to list of edges
        """
        groups = {}
        
        for edge in graph.edges():
            source, target = edge
            edge_data = graph[source][target]
            
            # Determine edge properties
            color = self._get_edge_color(source, target, highlight_node, start_wallet)
            width = self._get_edge_width(edge_data)
            style = 'solid' if highlight_node is None or highlight_node in edge else 'dash'
            
            props = (color, width, style)
            
            if props not in groups:
                groups[props] = []
            groups[props].append(edge)
        
        return groups
    
    def _create_edge_group_trace(
        self,
        edges: List[tuple],
        pos: Dict[str, Tuple[float, float]],
        props: tuple
    ) -> go.Scatter:
        """Create trace for a group of edges with same properties."""
        edge_x = []
        edge_y = []
        hover_text = []
        
        color, width, style = props
        
        for edge in edges:
            source, target = edge
            
            if source not in pos or target not in pos:
                continue
            
            x0, y0 = pos[source]
            x1, y1 = pos[target]
            
            # Add edge coordinates
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            # Hover text for edge
            hover_text.extend([
                f"{self._truncate_address(source)} → {self._truncate_address(target)}",
                f"{self._truncate_address(source)} → {self._truncate_address(target)}",
                None
            ])
        
        if not edge_x:
            return None
        
        # Determine dash pattern
        dash = None if style == 'solid' else 'dash'
        
        return go.Scatter(
            x=edge_x,
            y=edge_y,
            mode='lines',
            line=dict(
                width=width,
                color=color,
                dash=dash
            ),
            hoverinfo='text',
            text=hover_text,
            showlegend=False
        )
    
    def _get_edge_color(
        self,
        source: str,
        target: str,
        highlight_node: Optional[str] = None,
        start_wallet: Optional[str] = None
    ) -> str:
        """Determine edge color based on highlighting rules."""
        # If highlighting is active
        if highlight_node:
            if highlight_node in [source, target]:
                return self.HIGHLIGHTED_EDGE_COLOR
            else:
                return 'rgba(150, 150, 150, 0.1)'  # Very faint
        
        # Special color for edges connected to start wallet
        if start_wallet and start_wallet in [source, target]:
            return 'rgba(255, 215, 0, 0.4)'  # Gold
        
        return self.DEFAULT_EDGE_COLOR
    
    def _get_edge_width(self, edge_data: Dict) -> float:
        """Calculate edge width based on transaction count or amount."""
        # Use transaction count for width
        tx_count = edge_data.get('transaction_count', 1)
        
        # Logarithmic scaling for better visual distribution
        if tx_count <= 1:
            width = self.MIN_EDGE_WIDTH
        else:
            # Scale logarithmically
            import math
            width = self.MIN_EDGE_WIDTH + math.log10(tx_count) * 1.5
        
        return min(width, self.MAX_EDGE_WIDTH)
    
    def _truncate_address(self, address: str, length: int = 6) -> str:
        """Truncate wallet address for display."""
        if len(address) <= length * 2:
            return address
        return f"{address[:length]}...{address[-length:]}"
    
    def create_edge_legend(self) -> go.Scatter:
        """Create legend trace explaining edge width meaning."""
        return go.Scatter(
            x=[None],
            y=[None],
            mode='lines',
            name='Transaction Volume',
            line=dict(
                width=2,
                color=self.DEFAULT_EDGE_COLOR
            ),
            showlegend=True
        )
