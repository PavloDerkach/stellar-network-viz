"""
Graph builder for network visualization.
"""
import networkx as nx
import plotly.graph_objects as go
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NetworkGraphBuilder:
    """Build and analyze network graphs from wallet and transaction data."""
    
    def __init__(self):
        """Initialize graph builder."""
        self.graph = None
        self.positions = None
        self.layout_cache = {}
    
    def build_graph(
        self,
        wallets: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        directed: bool = True
    ) -> nx.Graph:
        """
        Build NetworkX graph from wallet and transaction data.
        
        Args:
            wallets: Dictionary of wallet data
            transactions: List of transaction data
            directed: Whether to create directed graph
            
        Returns:
            NetworkX graph object
        """
        # Create graph
        if directed:
            G = nx.DiGraph()
        else:
            G = nx.Graph()
        
        # Add nodes (wallets)
        for wallet_id, wallet_data in wallets.items():
            G.add_node(
                wallet_id,
                balance=float(wallet_data.get("balance_xlm", 0)),
                created_at=wallet_data.get("created_at"),
                label=self._create_wallet_label(wallet_id),
                **wallet_data
            )
        
        # Add edges (transactions)
        for tx in transactions:
            if "from" in tx and "to" in tx:
                source = tx["from"]
                target = tx["to"]
                
                # Only add edge if both nodes exist
                if source in G.nodes and target in G.nodes:
                    amount = float(tx.get("amount", 0))
                    
                    if G.has_edge(source, target):
                        # Update existing edge
                        G[source][target]["weight"] += amount
                        G[source][target]["count"] += 1
                    else:
                        # Add new edge
                        G.add_edge(
                            source,
                            target,
                            weight=amount,
                            count=1,
                            asset=tx.get("asset_code", "XLM"),
                            first_tx=tx.get("created_at"),
                            last_tx=tx.get("created_at")
                        )
        
        self.graph = G
        return G
    
    def calculate_layout(
        self,
        graph: nx.Graph,
        layout_type: str = "spring",
        **kwargs
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate node positions for graph layout.
        
        Args:
            graph: NetworkX graph
            layout_type: Type of layout algorithm
            **kwargs: Additional layout parameters
            
        Returns:
            Dictionary of node positions
        """
        # Check cache
        cache_key = f"{layout_type}_{graph.number_of_nodes()}_{graph.number_of_edges()}"
        if cache_key in self.layout_cache:
            return self.layout_cache[cache_key]
        
        # Calculate layout based on type
        if layout_type == "spring" or layout_type == "force":
            pos = nx.spring_layout(graph, k=kwargs.get("k", 1), iterations=kwargs.get("iterations", 50))
        elif layout_type == "circular":
            pos = nx.circular_layout(graph)
        elif layout_type == "hierarchical":
            pos = self._hierarchical_layout(graph)
        elif layout_type == "kamada":
            pos = nx.kamada_kawai_layout(graph)
        elif layout_type == "spectral":
            pos = nx.spectral_layout(graph)
        elif layout_type == "community":
            pos = self._community_layout(graph)
        else:
            pos = nx.spring_layout(graph)
        
        # Cache result
        self.layout_cache[cache_key] = pos
        self.positions = pos
        
        return pos
    
    def create_plotly_figure(
        self,
        graph: nx.Graph,
        layout_type: str = "spring",
        node_size_metric: str = "degree",
        show_labels: bool = True,
        **kwargs
    ) -> go.Figure:
        """
        Create Plotly figure from NetworkX graph.
        
        Args:
            graph: NetworkX graph
            layout_type: Layout algorithm to use
            node_size_metric: Metric to determine node size
            show_labels: Whether to show node labels
            **kwargs: Additional parameters
            
        Returns:
            Plotly figure object
        """
        # Calculate positions
        pos = self.calculate_layout(graph, layout_type, **kwargs)
        
        # Create figure
        fig = go.Figure()
        
        # Add edges
        edge_traces = self._create_edge_traces(graph, pos)
        for trace in edge_traces:
            fig.add_trace(trace)
        
        # Add nodes
        node_trace = self._create_node_trace(
            graph, pos, 
            size_metric=node_size_metric,
            show_labels=show_labels
        )
        fig.add_trace(node_trace)
        
        # Update layout
        fig.update_layout(
            title="Stellar Wallet Network",
            showlegend=False,
            hovermode="closest",
            margin=dict(b=0, l=0, r=0, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=600,
            clickmode="event+select"
        )
        
        return fig
    
    def analyze_network(self, graph: nx.Graph) -> Dict[str, Any]:
        """
        Analyze network and calculate metrics.
        
        Args:
            graph: NetworkX graph
            
        Returns:
            Dictionary of network metrics
        """
        metrics = {}
        
        # Basic metrics
        metrics["num_nodes"] = graph.number_of_nodes()
        metrics["num_edges"] = graph.number_of_edges()
        metrics["density"] = nx.density(graph)
        
        # Degree metrics
        degrees = dict(graph.degree())
        metrics["avg_degree"] = np.mean(list(degrees.values()))
        metrics["max_degree"] = max(degrees.values()) if degrees else 0
        metrics["min_degree"] = min(degrees.values()) if degrees else 0
        
        # Centrality metrics
        if graph.number_of_nodes() > 0:
            metrics["degree_centrality"] = nx.degree_centrality(graph)
            
            if graph.number_of_nodes() > 1:
                try:
                    metrics["betweenness_centrality"] = nx.betweenness_centrality(graph)
                    metrics["closeness_centrality"] = nx.closeness_centrality(graph)
                except:
                    logger.warning("Could not calculate some centrality metrics")
        
        # Component analysis
        if graph.is_directed():
            components = list(nx.weakly_connected_components(graph))
        else:
            components = list(nx.connected_components(graph))
        
        metrics["num_components"] = len(components)
        if components:
            metrics["largest_component_size"] = len(max(components, key=len))
        
        # Clustering coefficient
        if not graph.is_directed():
            metrics["avg_clustering"] = nx.average_clustering(graph)
        
        # Path metrics (for small graphs)
        if graph.number_of_nodes() < 100:
            try:
                if nx.is_connected(graph.to_undirected() if graph.is_directed() else graph):
                    metrics["avg_shortest_path"] = nx.average_shortest_path_length(graph)
                    metrics["diameter"] = nx.diameter(graph.to_undirected() if graph.is_directed() else graph)
            except:
                logger.warning("Could not calculate path metrics")
        
        return metrics
    
    def detect_communities(self, graph: nx.Graph, method: str = "louvain") -> Dict[str, List[str]]:
        """
        Detect communities in the network.
        
        Args:
            graph: NetworkX graph
            method: Community detection method
            
        Returns:
            Dictionary of communities
        """
        # Convert to undirected if necessary
        if graph.is_directed():
            G = graph.to_undirected()
        else:
            G = graph
        
        communities = {}
        
        if method == "louvain":
            try:
                import community as community_louvain
                partition = community_louvain.best_partition(G)
                
                # Group nodes by community
                for node, comm_id in partition.items():
                    if comm_id not in communities:
                        communities[comm_id] = []
                    communities[comm_id].append(node)
            except ImportError:
                logger.warning("python-louvain not installed, using greedy modularity")
                method = "greedy"
        
        if method == "greedy":
            from networkx.algorithms import community
            comms = community.greedy_modularity_communities(G)
            for i, comm in enumerate(comms):
                communities[i] = list(comm)
        
        return communities
    
    def find_important_nodes(
        self,
        graph: nx.Graph,
        metric: str = "degree",
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Find most important nodes in the network.
        
        Args:
            graph: NetworkX graph
            metric: Metric to use for importance
            top_n: Number of top nodes to return
            
        Returns:
            List of (node_id, score) tuples
        """
        if metric == "degree":
            scores = dict(graph.degree())
        elif metric == "betweenness":
            scores = nx.betweenness_centrality(graph)
        elif metric == "closeness":
            scores = nx.closeness_centrality(graph)
        elif metric == "pagerank":
            scores = nx.pagerank(graph)
        elif metric == "eigenvector":
            try:
                scores = nx.eigenvector_centrality(graph, max_iter=1000)
            except:
                logger.warning("Eigenvector centrality failed, using degree")
                scores = dict(graph.degree())
        else:
            scores = dict(graph.degree())
        
        # Sort by score and return top N
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:top_n]
    
    def _create_wallet_label(self, wallet_id: str) -> str:
        """Create shortened label for wallet."""
        if len(wallet_id) > 16:
            return f"{wallet_id[:6]}...{wallet_id[-4:]}"
        return wallet_id
    
    def _hierarchical_layout(self, graph: nx.Graph) -> Dict:
        """Create hierarchical layout for directed graphs."""
        if graph.is_directed():
            # Find nodes with no incoming edges (roots)
            roots = [n for n in graph.nodes() if graph.in_degree(n) == 0]
            if not roots:
                # If no roots, use node with highest out-degree
                roots = [max(graph.nodes(), key=lambda n: graph.out_degree(n))]
            
            # Create tree from roots
            try:
                # Use graphviz layout if available
                pos = nx.nx_agraph.graphviz_layout(graph, prog="dot")
            except:
                # Fallback to simple hierarchical layout
                pos = self._simple_hierarchical_layout(graph, roots)
        else:
            pos = nx.spring_layout(graph)
        
        return pos
    
    def _simple_hierarchical_layout(self, graph: nx.Graph, roots: List[str]) -> Dict:
        """Simple hierarchical layout implementation."""
        pos = {}
        visited = set()
        level = 0
        current_level = roots
        
        while current_level:
            # Position nodes at current level
            for i, node in enumerate(current_level):
                if node not in visited:
                    pos[node] = (i - len(current_level)/2, -level)
                    visited.add(node)
            
            # Get next level
            next_level = []
            for node in current_level:
                for successor in graph.successors(node):
                    if successor not in visited:
                        next_level.append(successor)
            
            current_level = next_level
            level += 1
        
        # Add any remaining nodes
        remaining = set(graph.nodes()) - visited
        for i, node in enumerate(remaining):
            pos[node] = (i - len(remaining)/2, -level)
        
        return pos
    
    def _community_layout(self, graph: nx.Graph) -> Dict:
        """Layout based on community structure."""
        # Detect communities
        communities = self.detect_communities(graph)
        
        pos = {}
        
        # Layout each community
        for comm_id, nodes in communities.items():
            # Create subgraph for community
            subgraph = graph.subgraph(nodes)
            
            # Layout community
            comm_pos = nx.spring_layout(subgraph, k=0.5)
            
            # Offset community position
            offset_x = comm_id * 3
            offset_y = 0
            
            for node, (x, y) in comm_pos.items():
                pos[node] = (x + offset_x, y + offset_y)
        
        return pos
    
    def _create_edge_traces(
        self,
        graph: nx.Graph,
        pos: Dict[str, Tuple[float, float]]
    ) -> List[go.Scatter]:
        """Create edge traces for Plotly figure."""
        traces = []
        
        for edge in graph.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            weight = edge[2].get("weight", 1)
            count = edge[2].get("count", 1)
            
            # Scale edge width based on weight
            width = min(0.5 + np.log1p(weight) / 10, 5)
            
            edge_trace = go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(
                    width=width,
                    color="#888"
                ),
                hoverinfo="text",
                text=f"From: {edge[0][:8]}...<br>To: {edge[1][:8]}...<br>Volume: {weight:.2f}<br>Transactions: {count}",
                showlegend=False
            )
            traces.append(edge_trace)
        
        return traces
    
    def _create_node_trace(
        self,
        graph: nx.Graph,
        pos: Dict[str, Tuple[float, float]],
        size_metric: str = "degree",
        show_labels: bool = True
    ) -> go.Scatter:
        """Create node trace for Plotly figure."""
        node_x = []
        node_y = []
        node_text = []
        node_hover = []
        node_sizes = []
        node_colors = []
        
        # Calculate node metrics
        if size_metric == "degree":
            sizes = dict(graph.degree())
        elif size_metric == "balance":
            sizes = {n: graph.nodes[n].get("balance", 1) for n in graph.nodes()}
        elif size_metric == "volume":
            sizes = {}
            for node in graph.nodes():
                volume = sum(graph[node][neighbor].get("weight", 0) 
                           for neighbor in graph.neighbors(node))
                sizes[node] = volume
        else:
            sizes = {n: 1 for n in graph.nodes()}
        
        # Normalize sizes
        if sizes:
            min_size = min(sizes.values())
            max_size = max(sizes.values())
            if max_size > min_size:
                normalized_sizes = {
                    n: 10 + 40 * (sizes[n] - min_size) / (max_size - min_size)
                    for n in sizes
                }
            else:
                normalized_sizes = {n: 25 for n in sizes}
        else:
            normalized_sizes = {}
        
        # Build node data
        for node in graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Node label
            if show_labels:
                node_text.append(graph.nodes[node].get("label", node[:8]))
            else:
                node_text.append("")
            
            # Hover text
            degree = graph.degree(node)
            balance = graph.nodes[node].get("balance", 0)
            
            hover_text = (
                f"<b>{node[:12]}...</b><br>"
                f"Balance: {balance:.2f} XLM<br>"
                f"Connections: {degree}<br>"
            )
            
            # Add volume info
            if graph.is_directed():
                in_volume = sum(graph[pred][node].get("weight", 0) 
                              for pred in graph.predecessors(node))
                out_volume = sum(graph[node][succ].get("weight", 0) 
                               for succ in graph.successors(node))
                hover_text += f"In Volume: {in_volume:.2f}<br>Out Volume: {out_volume:.2f}"
            else:
                volume = sum(graph[node][neighbor].get("weight", 0) 
                           for neighbor in graph.neighbors(node))
                hover_text += f"Total Volume: {volume:.2f}"
            
            node_hover.append(hover_text)
            
            # Node size
            node_sizes.append(normalized_sizes.get(node, 25))
            
            # Node color (can be based on various metrics)
            node_colors.append(degree)
        
        # Create trace
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text" if show_labels else "markers",
            hoverinfo="text",
            text=node_text,
            hovertext=node_hover,
            textposition="top center",
            marker=dict(
                size=node_sizes,
                color=node_colors,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(
                    title="Connections",
                    thickness=15,
                    len=0.7,
                    x=1.02
                ),
                line=dict(width=2, color="white")
            )
        )
        
        return node_trace
