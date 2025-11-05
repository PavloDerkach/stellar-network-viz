"""Node renderer for graph visualization."""

from typing import Dict, List, Optional, Any, Tuple
import networkx as nx
import plotly.graph_objects as go
import colorsys


class NodeRenderer:
    """Handles node rendering for graph visualization."""
    
    # Visual constants
    START_WALLET_MULTIPLIER = 3.0
    DEFAULT_NODE_SIZE = 30
    MIN_NODE_SIZE = 15
    MAX_NODE_SIZE = 60
    
    # Colors
    START_WALLET_COLOR = '#FFD700'  # Gold
    DEFAULT_NODE_COLOR = '#4A90E2'  # Blue
    HIGHLIGHTED_COLOR = '#FF6B6B'   # Red
    
    def __init__(self):
        """Initialize node renderer."""
        self.node_traces = []
    
    def create_node_traces(
        self,
        graph: nx.Graph,
        pos: Dict[str, Tuple[float, float]],
        start_wallet: Optional[str] = None,
        highlight_node: Optional[str] = None,
        clicked_node: Optional[str] = None,
        show_labels: bool = True
    ) -> List[go.Scatter]:
        """
        Create Plotly traces for nodes.
        
        Args:
            graph: NetworkX graph
            pos: Node positions
            start_wallet: Starting wallet to emphasize
            highlight_node: Node to highlight
            clicked_node: Currently clicked node
            show_labels: Whether to show node labels
            
        Returns:
            List of Plotly scatter traces
        """
        traces = []
        
        # Main node trace
        node_trace = self._create_main_node_trace(
            graph, pos, start_wallet, highlight_node, clicked_node
        )
        traces.append(node_trace)
        
        # Label trace
        if show_labels:
            label_trace = self._create_label_trace(
                graph, pos, start_wallet
            )
            traces.append(label_trace)
        
        # Border trace for emphasized nodes
        border_trace = self._create_border_trace(
            graph, pos, start_wallet, clicked_node
        )
        if border_trace:
            traces.append(border_trace)
        
        return traces
    
    def _create_main_node_trace(
        self,
        graph: nx.Graph,
        pos: Dict[str, Tuple[float, float]],
        start_wallet: Optional[str] = None,
        highlight_node: Optional[str] = None,
        clicked_node: Optional[str] = None
    ) -> go.Scatter:
        """Create main node trace with colors and sizes."""
        node_x = []
        node_y = []
        node_colors = []
        node_sizes = []
        node_symbols = []
        node_text = []
        customdata = []
        
        for node in graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Determine node size
            size = self._calculate_node_size(graph, node, start_wallet)
            node_sizes.append(size)
            
            # Determine node color
            color = self._get_node_color(graph, node, start_wallet, highlight_node)
            node_colors.append(color)
            
            # Determine node symbol
            symbol = self._get_node_symbol(node, start_wallet, clicked_node)
            node_symbols.append(symbol)
            
            # Node text for hover
            node_text.append(self._truncate_address(node))
            customdata.append(node)
        
        return go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers',
            marker=dict(
                size=node_sizes,
                color=node_colors,
                symbol=node_symbols,
                line=dict(width=0),
                colorscale='Viridis',
                showscale=False
            ),
            text=node_text,
            customdata=customdata,
            hovertemplate='%{text}<extra></extra>',
            hoverlabel=dict(
                bgcolor='white',
                font=dict(size=12)
            ),
            name='Wallets'
        )
    
    def _create_label_trace(
        self,
        graph: nx.Graph,
        pos: Dict[str, Tuple[float, float]],
        start_wallet: Optional[str] = None
    ) -> go.Scatter:
        """Create trace for node labels."""
        label_x = []
        label_y = []
        label_text = []
        
        for node in graph.nodes():
            x, y = pos[node]
            label_x.append(x)
            label_y.append(y)
            
            # Show truncated address or special label
            if node == start_wallet:
                label = f"START: {self._truncate_address(node, 6)}"
            else:
                label = self._truncate_address(node, 4)
            
            label_text.append(label)
        
        return go.Scatter(
            x=label_x,
            y=label_y,
            mode='text',
            text=label_text,
            textposition='bottom center',
            textfont=dict(
                size=9,
                color='#666'
            ),
            hoverinfo='skip',
            showlegend=False
        )
    
    def _create_border_trace(
        self,
        graph: nx.Graph,
        pos: Dict[str, Tuple[float, float]],
        start_wallet: Optional[str] = None,
        clicked_node: Optional[str] = None
    ) -> Optional[go.Scatter]:
        """Create border trace for emphasized nodes."""
        border_x = []
        border_y = []
        border_sizes = []
        
        for node in graph.nodes():
            if node in [start_wallet, clicked_node]:
                x, y = pos[node]
                border_x.append(x)
                border_y.append(y)
                
                # Slightly larger than the node
                size = self._calculate_node_size(graph, node, start_wallet)
                border_sizes.append(size + 5)
        
        if not border_x:
            return None
        
        return go.Scatter(
            x=border_x,
            y=border_y,
            mode='markers',
            marker=dict(
                size=border_sizes,
                color='rgba(255, 215, 0, 0.3)',  # Gold with transparency
                line=dict(
                    width=2,
                    color='#FFD700'
                )
            ),
            hoverinfo='skip',
            showlegend=False
        )
    
    def _calculate_node_size(
        self,
        graph: nx.Graph,
        node: str,
        start_wallet: Optional[str] = None
    ) -> float:
        """Calculate node size based on metrics."""
        if node == start_wallet:
            return self.DEFAULT_NODE_SIZE * self.START_WALLET_MULTIPLIER
        
        # Size based on degree (number of connections)
        degree = graph.degree(node)
        
        # Logarithmic scaling for better visual distribution
        if degree > 1:
            size = self.MIN_NODE_SIZE + (degree ** 0.5) * 5
        else:
            size = self.MIN_NODE_SIZE
        
        return min(size, self.MAX_NODE_SIZE)
    
    def _get_node_color(
        self,
        graph: nx.Graph,
        node: str,
        start_wallet: Optional[str] = None,
        highlight_node: Optional[str] = None
    ) -> str:
        """Get node color based on its role and state."""
        if node == start_wallet:
            return self.START_WALLET_COLOR
        
        if highlight_node and node != highlight_node:
            # Dim non-highlighted nodes
            return 'rgba(150, 150, 150, 0.3)'
        
        # Check if node has transactions in filtered currency
        node_data = graph.nodes[node]
        has_filtered_tx = node_data.get('has_filtered_transactions', True)
        
        if not has_filtered_tx:
            # Node has no transactions in selected currency - make semi-transparent
            return 'rgba(150, 150, 150, 0.2)'  # Gray, very transparent
        
        # Color based on transaction volume or balance
        # Use transaction count for color gradient
        tx_count = node_data.get('transaction_count', 1)
        
        # Create color gradient from blue to red based on activity
        hue = 0.6 - (min(tx_count, 100) / 100) * 0.4  # From blue to orange
        rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
        
        return f'rgb({int(rgb[0]*255)}, {int(rgb[1]*255)}, {int(rgb[2]*255)})'
    
    def _get_node_symbol(
        self,
        node: str,
        start_wallet: Optional[str] = None,
        clicked_node: Optional[str] = None
    ) -> str:
        """Get node symbol based on its role."""
        if node == clicked_node:
            return 'star'
        elif node == start_wallet:
            return 'diamond'
        else:
            return 'hexagon'
    
    def _truncate_address(self, address: str, length: int = 8) -> str:
        """Truncate wallet address for display."""
        if len(address) <= length * 2:
            return address
        return f"{address[:length]}...{address[-length:]}"
