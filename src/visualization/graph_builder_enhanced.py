"""
Enhanced graph builder with advanced interactivity for network visualization.
Improvements:
- Hover highlighting (show only node and its connections)
- Clickable nodes to recenter the graph
- Enhanced tooltips with transaction details
- Better visual feedback
"""
import networkx as nx
import plotly.graph_objects as go
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EnhancedNetworkGraphBuilder:
    """Enhanced graph builder with interactive features."""
    
    # Константы для размеров узлов
    FIXED_NODE_SIZE = 25  # Увеличен размер для лучшей видимости
    START_WALLET_MULTIPLIER = 2.0  # Центральный кошелек в 2 раза больше

    def __init__(self):
        """Initialize enhanced graph builder."""
        self.graph = None
        self.positions = None
        self.layout_cache = {}
        self.center_node = None  # Track which node is centered

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

        # Add nodes (wallets) - FOR BOTH directed and undirected!
        for wallet_id, wallet_data in wallets.items():
            # Extract specific fields we want to set
            node_attrs = {
                "label": self._create_wallet_label(wallet_id),
                "transaction_count": 0,
                "total_sent": 0,
                "total_received": 0,
            }
            # Add all wallet_data attributes
            node_attrs.update(wallet_data)
            # Ensure balance is float
            if "balance_xlm" in node_attrs:
                node_attrs["balance"] = float(node_attrs.get("balance_xlm", 0))

            G.add_node(wallet_id, **node_attrs)

        # Add edges (transactions) and update node statistics
        for tx in transactions:
            if "from" in tx and "to" in tx:
                source = tx["from"]
                target = tx["to"]

                # Only add edge if both nodes exist
                if source in G.nodes and target in G.nodes:
                    amount = float(tx.get("amount", 0))
                    asset = tx.get("asset_code", "XLM")

                    # Update node statistics
                    G.nodes[source]["transaction_count"] += 1
                    G.nodes[source]["total_sent"] += amount
                    G.nodes[target]["transaction_count"] += 1
                    G.nodes[target]["total_received"] += amount

                    # Create edge key for multi-asset support
                    edge_key = (source, target)

                    if G.has_edge(source, target):
                        # Update existing edge
                        G[source][target]["weight"] += amount
                        G[source][target]["count"] += 1

                        # Track assets
                        if "assets" not in G[source][target]:
                            G[source][target]["assets"] = {}
                        if asset not in G[source][target]["assets"]:
                            G[source][target]["assets"][asset] = 0
                        G[source][target]["assets"][asset] += amount
                    else:
                        # Add new edge
                        G.add_edge(
                            source,
                            target,
                            weight=amount,
                            count=1,
                            asset=asset,
                            assets={asset: amount},
                            first_tx=tx.get("created_at"),
                            last_tx=tx.get("created_at"),
                            tx_type=tx.get("type", "payment")
                        )

        self.graph = G
        return G

    def _create_wallet_label(self, wallet_id: str) -> str:
        """Create short label for wallet."""
        return f"{wallet_id[:4]}...{wallet_id[-4:]}"

    def calculate_layout(
            self,
            graph: nx.Graph,
            layout_type: str = "spring",
            center_node: Optional[str] = None,
            start_wallet: Optional[str] = None,
            **kwargs
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate node positions for graph layout.
        
        Args:
            graph: NetworkX graph
            layout_type: Type of layout algorithm
            center_node: Node to center (if applicable)
            **kwargs: Additional layout parameters
            
        Returns:
            Dictionary of node positions
        """
        self.center_node = center_node

        # Check cache (only if no center node is specified)
        cache_key = f"{layout_type}_{graph.number_of_nodes()}_{graph.number_of_edges()}"
        if center_node is None and cache_key in self.layout_cache:
            return self.layout_cache[cache_key]

        # Calculate layout based on type
        try:
            # Use start_wallet as center if no center_node specified
            actual_center = center_node if center_node else start_wallet
            
            if layout_type == "spring" or layout_type == "force":
                if actual_center and actual_center in graph.nodes():
                    # КАСТОМНЫЙ LAYOUT с учетом частоты транзакций!
                    pos = self._transaction_weighted_layout(
                        graph, 
                        center_node=actual_center,
                        node_size=self.FIXED_NODE_SIZE
                    )
                else:
                    n_nodes = len(graph.nodes())
                    optimal_k = 3.0 / np.sqrt(n_nodes) if n_nodes > 1 else 1.0
                    
                    pos = nx.spring_layout(
                        graph, 
                        k=optimal_k,  # БОЛЬШОЕ отталкивание
                        iterations=200,  # Много итераций
                        scale=8.0,  # ОЧЕНЬ БОЛЬШОЙ масштаб!
                        seed=42
                    )

            elif layout_type == "circular":
                if center_node and center_node in graph.nodes():
                    # Put center node in middle, others in circle
                    other_nodes = [n for n in graph.nodes() if n != center_node]
                    pos = nx.circular_layout(graph.subgraph(other_nodes), scale=2)
                    pos[center_node] = (0, 0)
                else:
                    pos = nx.circular_layout(graph)

            elif layout_type == "hierarchical":
                pos = self._hierarchical_layout(graph)

            elif layout_type == "kamada":
                pos = nx.kamada_kawai_layout(graph)

            elif layout_type == "spectral":
                if graph.number_of_nodes() > 1:
                    pos = nx.spectral_layout(graph)
                else:
                    pos = {list(graph.nodes())[0]: (0, 0)}

            elif layout_type == "community":
                pos = self._community_layout(graph)

            else:
                pos = nx.spring_layout(graph)

        except Exception as e:
            logger.warning(f"Layout calculation failed for {layout_type}: {e}. Falling back to spring layout.")
            pos = nx.spring_layout(graph, iterations=50)

        # Cache result (only if no center node)
        if center_node is None:
            self.layout_cache[cache_key] = pos

        self.positions = pos
        return pos

    def create_interactive_figure(
            self,
            graph: nx.Graph,
            layout_type: str = "spring",
            node_size_metric: str = "degree",
            show_labels: bool = True,
            highlight_node: Optional[str] = None,
            center_node: Optional[str] = None,
            start_wallet: Optional[str] = None,
            selected_asset: str = "XLM",  # ← NEW: Selected asset for tooltips
            **kwargs
    ) -> go.Figure:
        """
        Create interactive Plotly figure with hover highlighting.
        
        Args:
            graph: NetworkX graph
            layout_type: Layout algorithm to use
            node_size_metric: Metric to determine node size
            show_labels: Whether to show node labels
            highlight_node: Node to highlight (show only its connections)
            center_node: Node to center the graph on
            start_wallet: Starting wallet address (will be visually emphasized)
            **kwargs: Additional parameters
            
        Returns:
            Plotly figure object with interactive features
        """
        # Safety check
        if graph is None or len(graph.nodes()) == 0:
            # Return empty figure with message
            fig = go.Figure()
            fig.add_annotation(
                text="No data to display",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=20, color="gray")
            )
            return fig
        
        try:
            # Auto-center on start_wallet if no explicit center specified
            effective_center = center_node if center_node else start_wallet
            
            # Calculate positions
            pos = self.calculate_layout(graph, layout_type, center_node=effective_center, start_wallet=start_wallet, **kwargs)

            # Create figure
            fig = go.Figure()

            # Determine which edges and nodes to show based on highlight
            if highlight_node and highlight_node in graph.nodes():
                # Show only edges connected to highlighted node
                visible_edges = [
                    (u, v) for u, v in graph.edges()
                    if u == highlight_node or v == highlight_node
                ]
                visible_nodes = {highlight_node}
                for u, v in visible_edges:
                    visible_nodes.add(u)
                    visible_nodes.add(v)
            else:
                visible_edges = list(graph.edges())
                visible_nodes = set(graph.nodes())

            # Add edges with enhanced hover info
            edge_traces = self._create_enhanced_edge_traces(
                graph, pos, visible_edges, start_wallet=start_wallet
            )
            for trace in edge_traces:
                fig.add_trace(trace)

            # Add nodes with enhanced interactivity
            node_trace = self._create_interactive_node_trace(
                graph, pos,
                size_metric=node_size_metric,
                show_labels=show_labels,
                visible_nodes=visible_nodes,
                highlight_node=highlight_node,
                center_node=center_node,
                start_wallet=start_wallet,
                selected_asset=selected_asset  # ← PASS selected_asset
            )
            fig.add_trace(node_trace)

            # Update layout with better interactivity and FIXED axis range
            fig.update_layout(
                title={
                    'text': "Stellar Wallet Network" + (f" - Centered on {center_node[:8]}..." if center_node else ""),
                    'x': 0.5,
                    'xanchor': 'center'
                },
                showlegend=False,
                hovermode="closest",
                margin=dict(b=20, l=20, r=20, t=60),
                xaxis=dict(
                    showgrid=False, 
                    zeroline=False,
                    showticklabels=False,
                    autorange=True,  # ← AUTOSCALE!
                    scaleanchor="y",
                    scaleratio=1
                ),
                yaxis=dict(
                    showgrid=False, 
                    zeroline=False,
                    showticklabels=False,
                    autorange=True,  # ← AUTOSCALE!
                ),
                plot_bgcolor="white",
                paper_bgcolor="white",
                height=700,
                clickmode="event+select",
                dragmode="pan",
                uirevision="constant"  # Preserve UI state including zoom
            )
            
            # ========================
            # ПУНКТ 5: ADD COLOR LEGEND (Compact version with squares)
            # ========================
            # Add compact legend header (clickable in Streamlit)
            legend_html = (
                "<b>📊 Edge Colors</b><br>"
                "<span style='font-size:9px; color:#666;'>(See details below graph)</span>"
            )
            
            fig.add_annotation(
                text=legend_html,
                xref="paper", yref="paper",
                x=0.98, y=0.98,
                xanchor="right", yanchor="top",
                showarrow=False,
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor="#888888",
                borderwidth=1,
                borderpad=8,
                font=dict(size=11),
                align="left"
            )

            return fig
            
        except Exception as e:
            # Return error figure
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error creating graph: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16, color="red")
            )
            return fig

    def _transaction_weighted_layout(
            self,
            graph: nx.Graph,
            center_node: str,
            node_size: float = 20
    ) -> Dict[str, Tuple[float, float]]:
        """
        ПРОПОРЦИОНАЛЬНЫЙ layout: расстояние обратно пропорционально количеству транзакций.
        
        ПРАВИЛО:
        - 1 транзакция = 100% расстояния (КРАЙ графа)
        - Больше транзакций = ПРОПОРЦИОНАЛЬНО БЛИЖЕ к центру
        - Формула: distance = max_distance * (1 / tx_count)
        
        Args:
            graph: NetworkX граф
            center_node: Центральный узел (стартовый кошелек)
            node_size: Размер узла в пикселях
            
        Returns:
            Словарь позиций узлов
        """
        pos = {}
        
        # Центральный узел в центре (0, 0)
        pos[center_node] = (0.0, 0.0)
        
        # Правильное масштабирование размеров
        center_radius = (node_size * self.START_WALLET_MULTIPLIER) / 50.0
        regular_radius = node_size / 50.0
        
        # Минимальное расстояние между ЦЕНТРАМИ узлов
        min_node_separation = 3 * regular_radius  # 3 радиуса между центрами
        
        # Минимальное расстояние от центра
        min_distance_from_center = 4 * (center_radius * 2)  # 4 диаметра центрального узла
        
        # МАКСИМАЛЬНОЕ расстояние = для узлов с 1 транзакцией (КРАЙ ГРАФА)
        max_distance = 5.5  # Край графа - узлы с 1 транзакцией здесь!
        
        # Собираем информацию о транзакциях с центральным узлом
        neighbors = []
        tx_counts = {}  # Количество транзакций для каждого узла
        
        for node in graph.nodes():
            if node == center_node:
                continue
            
            # Считаем транзакции с центральным узлом
            tx_count = 0
            if graph.has_edge(center_node, node):
                tx_count += graph[center_node][node].get('count', 1)
            if graph.has_edge(node, center_node):
                tx_count += graph[node][center_node].get('count', 1)
            
            if tx_count > 0:
                neighbors.append((node, tx_count))
                tx_counts[node] = tx_count
        
        if not neighbors:
            return pos
        
        # Сортируем по количеству транзакций (больше транзакций = первые в списке)
        neighbors.sort(key=lambda x: x[1], reverse=True)
        
        # Находим максимальное количество транзакций
        max_tx = max(tx for _, tx in neighbors)
        
        logger.info(f"Layout: {len(neighbors)} nodes, tx range: 1 to {max_tx}")
        
        # Группируем узлы по кольцам на основе ПРОПОРЦИИ транзакций
        # Узлы с похожим количеством транзакций попадают в одно кольцо
        ring_distances = {}  # distance -> [nodes]
        
        for node, tx_count in neighbors:
            # КЛЮЧЕВАЯ ФОРМУЛА: обратная пропорция!
            # 1 транзакция = max_distance (край)
            # max_tx транзакций = min_distance (близко к центру)
            
            # Нормализуем: tx_count / max_tx дает значение от 1/max_tx до 1.0
            # Инвертируем: 1.0 / (tx_count / max_tx) = max_tx / tx_count
            # Это дает пропорциональное расстояние
            
            proportion = max_tx / tx_count  # Обратная пропорция
            
            # Нормализуем в диапазон [0, 1]
            # 1 tx: proportion = max_tx/1 = max_tx (максимум)
            # max_tx tx: proportion = max_tx/max_tx = 1 (минимум)
            # Нормализуем: (proportion - 1) / (max_tx - 1)
            if max_tx > 1:
                norm_proportion = (proportion - 1) / (max_tx - 1)
            else:
                norm_proportion = 0
            
            # Расстояние: min для max_tx, max для 1 tx
            distance = min_distance_from_center + norm_proportion * (max_distance - min_distance_from_center)
            
            # Округляем расстояние для группировки в кольца
            ring_dist = round(distance, 1)
            
            if ring_dist not in ring_distances:
                ring_distances[ring_dist] = []
            ring_distances[ring_dist].append((node, tx_count))
        
        # Размещаем узлы по кольцам
        placed = []  # (node, x, y, radius)
        
        for ring_dist in sorted(ring_distances.keys()):
            nodes_in_ring = ring_distances[ring_dist]
            num_nodes = len(nodes_in_ring)
            
            logger.info(f"Ring at {ring_dist:.2f}: {num_nodes} nodes")
            
            # Угловое распределение с небольшим смещением для каждого кольца
            angle_offset = ring_dist * 0.2  # Поворот для разных колец
            
            for i, (node, tx_count) in enumerate(nodes_in_ring):
                # Начальный угол
                base_angle = (2 * np.pi * i / num_nodes) + angle_offset
                
                # Пытаемся разместить узел без наложений
                angle = base_angle
                distance = ring_dist
                attempts = 0
                max_attempts = 100
                
                while attempts < max_attempts:
                    x = distance * np.cos(angle)
                    y = distance * np.sin(angle)
                    
                    collision = False
                    
                    # Проверка с центральным узлом
                    dist_to_center = np.sqrt(x**2 + y**2)
                    if dist_to_center < min_distance_from_center:
                        collision = True
                    
                    # Проверка с другими узлами
                    if not collision:
                        for _, px, py, pr in placed:
                            dist = np.sqrt((x - px)**2 + (y - py)**2)
                            min_dist = regular_radius + pr + min_node_separation
                            if dist < min_dist:
                                collision = True
                                break
                    
                    if not collision:
                        break
                    
                    # Корректируем при наложении
                    attempts += 1
                    if attempts < 50:
                        # Пробуем другие углы
                        angle = base_angle + (attempts * 0.15)
                    else:
                        # Немного увеличиваем расстояние
                        distance = ring_dist + ((attempts - 50) * min_node_separation * 0.2)
                        angle = base_angle + ((attempts - 50) * 0.2)
                    
                    x = distance * np.cos(angle)
                    y = distance * np.sin(angle)
                
                pos[node] = (x, y)
                placed.append((node, x, y, regular_radius))
        
        logger.info(f"Layout complete: {len(pos)} nodes placed out of {len(neighbors)} connected to center")
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Размещаем узлы БЕЗ прямой связи с центром!
        # Они будут размещены на периферии графа используя spring_layout
        unplaced_nodes = [n for n in graph.nodes() if n not in pos and n != center_node]
        
        if unplaced_nodes:
            logger.info(f"Placing {len(unplaced_nodes)} unconnected nodes on periphery...")
            
            # Создаем подграф из неразмещенных узлов
            subgraph = graph.subgraph(unplaced_nodes)
            
            # Используем spring layout для их размещения
            if len(unplaced_nodes) > 1:
                sub_pos = nx.spring_layout(
                    subgraph, 
                    k=2.0,  # Большое отталкивание
                    iterations=100,
                    scale=3.0,  # Масштаб
                    seed=42
                )
            else:
                # Один узел - разместим справа от центра
                sub_pos = {unplaced_nodes[0]: (max_distance, 0)}
            
            # Сдвигаем их на периферию (за кольцо с макс. расстоянием)
            periphery_offset = max_distance + 1.5  # За самым дальним кольцом
            
            for node, (x, y) in sub_pos.items():
                # Сдвигаем на периферию
                new_x = x + periphery_offset
                new_y = y
                pos[node] = (new_x, new_y)
        
        logger.info(f"Final layout: {len(pos)} nodes placed (total nodes in graph: {len(graph.nodes())})")
        return pos
    
    def _hierarchical_layout(self, graph: nx.Graph) -> Dict:
        """Hierarchical layout for directed graphs."""
        if graph.is_directed():
            # Find root nodes (nodes with no incoming edges)
            roots = [n for n in graph.nodes() if graph.in_degree(n) == 0]

            if not roots:
                # If no roots, use node with highest out-degree
                roots = [max(graph.nodes(), key=lambda n: graph.out_degree(n))]

            # Create hierarchical layout
            try:
                pos = self._simple_hierarchical_layout(graph, roots)
            except:
                pos = nx.spring_layout(graph)
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
                    pos[node] = (i - len(current_level) / 2, -level)
                    visited.add(node)

            # Get next level
            next_level = []
            for node in current_level:
                if graph.is_directed():
                    successors = graph.successors(node)
                else:
                    successors = graph.neighbors(node)

                for successor in successors:
                    if successor not in visited:
                        next_level.append(successor)

            current_level = next_level
            level += 1

        # Add any remaining nodes
        remaining = set(graph.nodes()) - visited
        for i, node in enumerate(remaining):
            pos[node] = (i - len(remaining) / 2, -level)

        return pos

    def _community_layout(self, graph: nx.Graph) -> Dict:
        """Layout based on community structure."""
        try:
            from networkx.algorithms import community
            comms = list(community.greedy_modularity_communities(
                graph.to_undirected() if graph.is_directed() else graph
            ))
        except:
            # Fallback: just use spring layout
            return nx.spring_layout(graph)

        pos = {}

        # Layout each community
        for comm_id, comm_nodes in enumerate(comms):
            # Create subgraph for community
            subgraph = graph.subgraph(comm_nodes)

            # Layout community
            comm_pos = nx.spring_layout(subgraph, k=0.5, iterations=30)

            # Offset community position in a circular arrangement
            angle = 2 * np.pi * comm_id / len(comms)
            offset_x = 3 * np.cos(angle)
            offset_y = 3 * np.sin(angle)

            for node, (x, y) in comm_pos.items():
                pos[node] = (x + offset_x, y + offset_y)

        return pos

    def _create_enhanced_edge_traces(
            self,
            graph: nx.Graph,
            pos: Dict[str, Tuple[float, float]],
            visible_edges: List[Tuple[str, str]],
            start_wallet: Optional[str] = None
    ) -> List[go.Scatter]:
        """Create enhanced edge traces with better hover info."""
        traces = []

        for edge in visible_edges:
            if len(edge) < 2:
                continue

            source, target = edge[0], edge[1]

            if source not in pos or target not in pos:
                continue

            x0, y0 = pos[source]
            x1, y1 = pos[target]

            edge_data = graph.get_edge_data(source, target, default={})
            weight = edge_data.get("weight", 1)
            count = edge_data.get("count", 1)
            assets = edge_data.get("assets", {})

            # Check if this edge is connected to start_wallet
            is_start_edge = (source == start_wallet or target == start_wallet) if start_wallet else False
            
            # Тонкие линии как на референсном графе!
            FIXED_LINE_WIDTH = 1  # Очень тонкие линии
            width = FIXED_LINE_WIDTH
            
            # Цвет зависит от ЧАСТОТЫ транзакций (count), не от объема!
            if is_start_edge:
                # Цвета для линий стартового кошелька
                if count >= 10:
                    color = "#FF4500"  # Ярко-красный оранжевый (10+ транзакций)
                elif count >= 5:
                    color = "#0066FF"  # 🔵 СИНИЙ (5-9 транзакций)
                elif count >= 2:
                    color = "#FFA500"  # Светло-оранжевый (2-4 транзакции)
                else:
                    color = "#00CC66"  # 🟢 ЗЕЛЁНЫЙ (1 транзакция)
            else:
                # Цвета для линий между другими кошельками
                if count >= 10:
                    color = "#666666"  # Темно-серый (10+ транзакций)
                elif count >= 5:
                    color = "#0066FF"  # 🔵 СИНИЙ (5-9 транзакций)
                elif count >= 2:
                    color = "#AAAAAA"  # Светло-серый (2-4 транзакции)
                else:
                    color = "#00CC66"  # 🟢 ЗЕЛЁНЫЙ (1 транзакция)

            # Create hover text with detailed info
            hover_text = (
                f"<b>Transaction Flow</b><br>"
                f"From: {source[:12]}...<br>"
                f"To: {target[:12]}...<br>"
                f"━━━━━━━━━━━━━━━━<br>"
                f"<b>Total Volume: {weight:.2f}</b><br>"
                f"<b>Transaction Count: {count}</b><br>"
            )

            # Add asset breakdown if multiple assets
            if len(assets) > 1:
                hover_text += "Assets:<br>"
                for asset, amount in assets.items():
                    hover_text += f"  • {asset}: {amount:.2f}<br>"

            # Opacity разная для start_edge и обычных линий
            opacity_value = 0.8 if is_start_edge else 0.3  # Оранжевые ярче, серые прозрачнее
            
            edge_trace = go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(
                    width=width,
                    color=color
                ),
                hoverinfo="text",
                hovertext=hover_text,
                showlegend=False,
                opacity=opacity_value  # Полупрозрачность как на референсе!
            )
            traces.append(edge_trace)

        return traces

    def _create_interactive_node_trace(
            self,
            graph: nx.Graph,
            pos: Dict[str, Tuple[float, float]],
            size_metric: str = "degree",
            show_labels: bool = True,
            visible_nodes: Optional[set] = None,
            highlight_node: Optional[str] = None,
            center_node: Optional[str] = None,
            start_wallet: Optional[str] = None,
            selected_asset: str = "XLM"  # ← ADD: Selected asset for formatting
    ) -> go.Scatter:
        """Create interactive node trace with enhanced hover and click."""
        if visible_nodes is None:
            visible_nodes = set(graph.nodes())

        node_x = []
        node_y = []
        node_text = []
        node_hover = []
        node_sizes = []
        node_colors = []
        node_ids = []
        node_line_widths = []  # For custom border widths

        # ВСЕ УЗЛЫ ОДИНАКОВОГО РАЗМЕРА!
        # Игнорируем size_metric - все узлы будут равны
        normalized_sizes = {n: self.FIXED_NODE_SIZE for n in graph.nodes()}

        # Build node data
        for node in graph.nodes():
            if node not in visible_nodes and highlight_node is not None:
                continue

            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_ids.append(node)

            # Node label
            if show_labels:
                node_text.append(graph.nodes[node].get("label", node[:8]))
            else:
                node_text.append("")

            # Enhanced hover text with full details
            degree = graph.degree(node)
            balance = graph.nodes[node].get("balance", 0)
            tx_count = graph.nodes[node].get("transaction_count", 0)
            total_sent = graph.nodes[node].get("total_sent", 0)
            total_received = graph.nodes[node].get("total_received", 0)

            # Calculate net flow
            net_flow = total_received - total_sent
            net_flow_emoji = "📈" if net_flow > 0 else "📉" if net_flow < 0 else "➖"
            
            # Add START WALLET marker if this is the starting wallet
            wallet_marker = "🎯 <b>START WALLET</b><br>" if node == start_wallet else ""
            
            # Format amounts with thousands separator and currency
            balance_str = f"{balance:,.4f} XLM"  # Balance всегда в XLM
            sent_str = f"{total_sent:,.2f} {selected_asset}" if total_sent > 0 else f"0.00 {selected_asset}"
            received_str = f"{total_received:,.2f} {selected_asset}" if total_received > 0 else f"0.00 {selected_asset}"
            net_flow_str = f"{abs(net_flow):,.2f} {selected_asset}"
            
            hover_text = (
                f"{wallet_marker}"
                f"<b>🏦 Wallet Address:</b><br>"
                f"<span style='font-size:9px; font-family:monospace'>{node}</span><br>"
                f"<i style='font-size:9px'>💡 Select in 'Highlight wallet' for full details</i><br>"
                f"━━━━━━━━━━━━━━━━━━━━<br>"
                f"💰 <b>Balance:</b> {balance_str}<br>"
                f"🔗 <b>Connections:</b> {degree} wallet(s)<br>"
                f"<i style='font-size:9px'>(Number of wallets connected to this one)</i><br>"
                f"━━━━━━━━━━━━━━━━━━━━<br>"
                f"<b>📊 Activity in Filtered Network:</b><br>"
                f"<i style='font-size:9px'>(Transactions matching your filters)</i><br>"
                f"  • <b>Total Transactions:</b> {tx_count}<br>"
                f"  • <b>Sent (Outgoing):</b> {sent_str}<br>"
                f"  • <b>Received (Incoming):</b> {received_str}<br>"
                f"  • <b>Net Flow:</b> {net_flow_emoji} {net_flow_str}<br>"
                f"━━━━━━━━━━━━━━━━━━━━<br>"
                f"<i style='font-size:9px'>Adjust filters to see different flows!</i>"
            )

            node_hover.append(hover_text)

            # Node size - START wallet is EXACTLY START_WALLET_MULTIPLIER larger
            base_size = normalized_sizes.get(node, self.FIXED_NODE_SIZE)
            if node == start_wallet:
                # Start wallet is START_WALLET_MULTIPLIER larger with thick border
                node_sizes.append(base_size * self.START_WALLET_MULTIPLIER)
                node_line_widths.append(4)  # Thick border for start wallet
            else:
                node_sizes.append(base_size)
                node_line_widths.append(2)  # Normal border

            # Node color - highlight special nodes (START WALLET has highest priority!)
            if node == start_wallet:
                node_colors.append("#FF4500")  # ОЧЕНЬ ЯРКИЙ оранжево-красный (OrangeRed)!
            elif node == center_node:
                node_colors.append("#FF0000")  # Red for centered node
            elif node == highlight_node:
                node_colors.append("#FF6B6B")  # Light red for highlighted
            elif highlight_node and node in visible_nodes and node != highlight_node:
                node_colors.append("#4ECDC4")  # Teal for connected nodes
            else:
                # Color by degree
                node_colors.append(degree)

        # Create trace with custom data for click events
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text" if show_labels else "markers",
            hoverinfo="text",
            text=node_text,
            hovertext=node_hover,
            textposition="top center",
            customdata=node_ids,  # Store node IDs for click events
            marker=dict(
                size=node_sizes,
                color=node_colors if (highlight_node or center_node or start_wallet) else node_colors,
                colorscale="Viridis" if not (highlight_node or center_node or start_wallet) else None,
                showscale=not (highlight_node or center_node or start_wallet),
                colorbar=dict(
                    title="Connections",
                    thickness=15,
                    len=0.7,
                    x=1.02
                ) if not (highlight_node or center_node or start_wallet) else None,
                line=dict(
                    width=node_line_widths,  # Используем переменную для разной толщины!
                    color="#000000"  # Чёрная обводка для максимального контраста
                )
            ),
            textfont=dict(
                size=10,
                color="#333"
            )
        )

        return node_trace
