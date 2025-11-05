"""
PyVis Network Graph Builder - НОВАЯ РЕАЛИЗАЦИЯ
Использует PyVis (vis.js) для правильного force-directed layout и интерактивности
"""
import networkx as nx
from pyvis.network import Network
from typing import Dict, List, Optional, Any
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


def get_xlm_to_usdc_rate() -> float:
    """Get current XLM to USDC exchange rate."""
    try:
        import requests
        response = requests.get(
            'https://horizon.stellar.org/order_book',
            params={
                'selling_asset_type': 'native',
                'buying_asset_code': 'USDC',
                'buying_asset_issuer': 'GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN'
            },
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            if 'bids' in data and len(data['bids']) > 0:
                return float(data['bids'][0]['price'])
    except Exception as e:
        logger.warning(f"Failed to fetch XLM/USDC rate: {e}")
    return 0.10  # Fallback


class PyVisGraphBuilder:
    """Network graph builder using PyVis."""
    
    def __init__(self):
        """Initialize PyVis graph builder."""
        self.graph = None
        logger.info("✅ PyVis Graph Builder initialized")
    
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
        logger.info(f"Creating graph with {len(wallets)} wallets and {len(transactions)} transactions")
        
        # Create graph
        G = nx.DiGraph() if directed else nx.Graph()
        
        # ВАЖНО: Сначала собираем edges, потом добавляем ТОЛЬКО нужные узлы!
        edge_data = {}
        nodes_in_transactions = set()  # Узлы которые участвуют в транзакциях
        
        for tx in transactions:
            source = tx.get("from")
            target = tx.get("to")
            amount = float(tx.get("amount", 0))
            asset = tx.get("asset", "XLM")
            
            if not source or not target:
                continue
            
            # Skip self-transactions (wallet to itself)
            if source == target:
                continue
            
            # Track nodes that have transactions
            nodes_in_transactions.add(source)
            nodes_in_transactions.add(target)
            
            # Create edge key
            edge_key = (source, target)
            
            if edge_key not in edge_data:
                edge_data[edge_key] = {
                    "weight": 0,
                    "count": 0,
                    "assets": {}
                }
            
            # Aggregate data
            edge_data[edge_key]["weight"] += amount
            edge_data[edge_key]["count"] += 1
            
            if asset not in edge_data[edge_key]["assets"]:
                edge_data[edge_key]["assets"][asset] = 0
            edge_data[edge_key]["assets"][asset] += amount
        
        # Add ONLY nodes that participate in transactions!
        for wallet_id in nodes_in_transactions:
            if wallet_id in wallets:
                wallet_data = wallets[wallet_id]
                G.add_node(
                    wallet_id,
                    balance=wallet_data.get("balance_xlm", 0),
                    label=wallet_id[:8] + "..."
                )
            else:
                # Node not in wallet details - add with minimal data
                G.add_node(
                    wallet_id,
                    balance=0,
                    label=wallet_id[:8] + "..."
                )
        
        # Add edges to graph
        for (source, target), data in edge_data.items():
            G.add_edge(source, target, **data)
        
        logger.info(f"Built graph with {len(G.nodes())} nodes and {len(G.edges())} edges")
        self.graph = G
        return G
    
    def _get_edge_color(
        self,
        source: str,
        target: str,
        count: int,
        start_wallet: Optional[str] = None
    ) -> str:
        """
        Get edge color based on transaction count and connection to start wallet.
        
        Args:
            source: Source wallet
            target: Target wallet
            count: Transaction count
            start_wallet: Starting wallet address
            
        Returns:
            Color hex string
        """
        # Check if connected to start wallet
        is_start_edge = (source == start_wallet or target == start_wallet) if start_wallet else False
        
        if is_start_edge:
            # Orange gradient for START wallet edges
            if count >= 10:
                return "#FF4500"  # Dark orange (10+ tx)
            elif count >= 5:
                return "#FF6B00"  # Orange (5-9 tx)
            elif count >= 2:
                return "#FFA500"  # Light orange (2-4 tx)
            else:
                return "#FFD700"  # Gold (1 tx)
        else:
            # Gray gradient for other edges
            if count >= 10:
                return "#666666"  # Dark gray (10+ tx)
            elif count >= 5:
                return "#888888"  # Medium gray (5-9 tx)
            elif count >= 2:
                return "#AAAAAA"  # Light gray (2-4 tx)
            else:
                return "#CCCCCC"  # Very light gray (1 tx)
    
    def _calculate_node_metrics(
        self,
        node: str,
        transactions: List[Dict[str, Any]],
        start_wallet: Optional[str],
        selected_asset: str
    ) -> Dict[str, Any]:
        """
        Calculate metrics for a node from filtered transactions.
        ЖЕЛЕЗОБЕТОННЫЙ расчет - учитывает ВСЕ отфильтрованные транзакции!
        
        Args:
            node: Node ID
            transactions: List of FILTERED transactions
            start_wallet: Start wallet address
            selected_asset: Selected asset for filtering
            
        Returns:
            Dictionary with metrics
        """
        # Filter transactions for this node
        node_txs = [
            tx for tx in transactions 
            if tx.get('from') == node or tx.get('to') == node
        ]
        
        # Calculate sent/received
        total_sent = sum(
            float(tx.get('amount', 0)) 
            for tx in node_txs 
            if tx.get('from') == node
        )
        
        total_received = sum(
            float(tx.get('amount', 0)) 
            for tx in node_txs 
            if tx.get('to') == node
        )
        
        # Calculate net flow
        net_flow = total_received - total_sent
        
        # Count transactions with START wallet
        if start_wallet:
            tx_with_start = [
                tx for tx in node_txs 
                if (tx.get('from') == start_wallet and tx.get('to') == node) or
                   (tx.get('to') == start_wallet and tx.get('from') == node)
            ]
            connections_with_start = len(tx_with_start)
        else:
            connections_with_start = 0
        
        return {
            'total_sent': total_sent,
            'total_received': total_received,
            'net_flow': net_flow,
            'tx_count': len(node_txs),
            'connections_with_start': connections_with_start
        }
    
    def _create_tooltip(
        self,
        node: str,
        balance: float,
        metrics: Dict[str, Any],
        selected_asset: str,
        start_wallet: Optional[str],
        is_start: bool
    ) -> str:
        """
        Create simple text tooltip for a node.
        PyVis НЕ РЕНДЕРИТ HTML - используем простой текст!
        
        Args:
            node: Node ID
            balance: Balance in XLM
            metrics: Node metrics
            selected_asset: Selected asset
            start_wallet: Start wallet address
            is_start: Whether this is the start wallet
            
        Returns:
            Plain text string for tooltip
        """
        # Convert balance if needed
        if selected_asset == "USDC":
            try:
                xlm_to_usdc = get_xlm_to_usdc_rate()
                balance_usdc = balance * xlm_to_usdc
                balance_str = f"{balance_usdc:,.2f} USDC (≈{balance:,.4f} XLM)"
            except:
                balance_str = f"{balance:,.4f} XLM"
        else:
            balance_str = f"{balance:,.4f} XLM"
        
        # Format amounts
        sent_str = f"{metrics['total_sent']:,.2f} {selected_asset}"
        received_str = f"{metrics['total_received']:,.2f} {selected_asset}"
        net_flow = metrics['net_flow']
        net_flow_emoji = "📈" if net_flow > 0 else "📉" if net_flow < 0 else "➖"
        net_flow_str = f"{abs(net_flow):,.2f} {selected_asset}"
        
        # Start wallet marker
        start_marker = "🎯 START WALLET\n" if is_start else ""
        
        # Start wallet short address
        if start_wallet:
            start_short = f"{start_wallet[:8]}...{start_wallet[-4:]}"
        else:
            start_short = "N/A"
        
        # Build tooltip as PLAIN TEXT (no HTML!)
        tooltip = f"""{start_marker}🏦 Wallet Address:
{node}

💡 Click to select this wallet
━━━━━━━━━━━━━━━━━━━━
💰 Balance: {balance_str}
━━━━━━━━━━━━━━━━━━━━
📊 Activity with {start_short}:
• Transactions: {metrics['connections_with_start']}
• This wallet → {start_short}: {sent_str}
• {start_short} → This wallet: {received_str}
• Net Flow: {net_flow_emoji} {net_flow_str}
━━━━━━━━━━━━━━━━━━━━
Adjust filters to see different flows!"""
        
        return tooltip
    
    def create_interactive_figure(
        self,
        graph: nx.Graph,
        layout_type: str = "force",
        node_size_metric: str = "degree",
        show_labels: bool = False,
        highlight_node: Optional[str] = None,
        center_node: Optional[str] = None,
        start_wallet: Optional[str] = None,
        selected_asset: str = "XLM",
        transactions: Optional[List[Dict[str, Any]]] = None,
        data_completeness: Optional[Dict[str, Any]] = None,
        clicked_node: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Create interactive PyVis network visualization.
        
        Args:
            graph: NetworkX graph
            layout_type: Layout algorithm (ignored for PyVis, uses force-directed)
            node_size_metric: Metric for node size (ignored)
            show_labels: Whether to show labels
            highlight_node: Node to highlight
            center_node: Node to center on (ignored)
            start_wallet: Starting wallet address
            selected_asset: Selected asset for calculations
            transactions: List of filtered transactions for metrics
            data_completeness: Data completeness info
            clicked_node: Currently clicked node
            
        Returns:
            HTML string of the network visualization
        """
        logger.info(f"Creating interactive figure with {len(graph.nodes())} nodes")
        logger.info(f"🎯 START WALLET: {start_wallet}")
        
        # Create PyVis network
        net = Network(
            height="700px",
            width="100%",
            bgcolor="#ffffff",
            font_color="#000000",
            directed=isinstance(graph, nx.DiGraph)
        )
        
        # ОПТИМИЗАЦИЯ ДЛЯ БОЛЬШИХ ГРАФОВ (300+ узлов)
        n_nodes = len(graph.nodes())
        
        if n_nodes > 100:
            logger.info(f"🚀 Using optimized physics for large graph ({n_nodes} nodes)")
            # Barnes-Hut алгоритм для больших графов - НАМНОГО быстрее!
            net.barnes_hut(
                gravity=-3000,              # Отталкивание узлов
                central_gravity=0.3,        # Притяжение к центру
                spring_length=250,          # Длина связей
                spring_strength=0.001,      # Сила пружин
                damping=0.09,              # Затухание
                overlap=0                   # Избегание наложений
            )
        else:
            # Для малых графов используем force_atlas_2based
            net.force_atlas_2based(
                gravity=-150,
                central_gravity=0.005,
                spring_length=300,
                spring_strength=0.02,
                damping=0.5,
                overlap=1
            )
        
        # Adaptive node size based on graph size
        n_nodes = len(graph.nodes())
        base_size = max(15, min(30, 500 / n_nodes))
        start_size = base_size * 1.5  # START wallet 1.5x bigger
        
        # Add nodes
        for node in graph.nodes():
            # Get balance
            balance = graph.nodes[node].get("balance_xlm", 0)
            
            # Calculate metrics from transactions
            if transactions:
                metrics = self._calculate_node_metrics(
                    node, transactions, start_wallet, selected_asset
                )
            else:
                # Fallback to graph attributes (should not happen)
                metrics = {
                    'total_sent': 0,
                    'total_received': 0,
                    'net_flow': 0,
                    'tx_count': 0,
                    'connections_with_start': graph.degree(node)
                }
            
            # Determine if this is start wallet
            is_start = (node == start_wallet)
            is_clicked = (node == clicked_node and node != start_wallet)
            
            if is_start:
                logger.info(f"✅ FOUND START WALLET NODE: {node[:12]}...")
            
            # Node size and shape
            if is_start:
                size = start_size
                shape = "diamond"
                color = "#FF4500"  # Bright orange-red
                border_width = 4
            elif is_clicked:
                size = base_size * 1.2
                shape = "star"
                color = "#FFD700"  # Gold
                border_width = 3
            else:
                size = base_size
                shape = "dot"
                color = "#4ECDC4"  # Teal
                border_width = 2
            
            # Create tooltip
            tooltip = self._create_tooltip(
                node, balance, metrics, selected_asset, start_wallet, is_start
            )
            
            # Add node to network
            label = graph.nodes[node].get("label", node[:8]) if show_labels else ""
            
            # ЦЕНТРИРУЕМ СТАРТОВЫЙ КОШЕЛЁК!
            if is_start:
                net.add_node(
                    node,
                    label=label,
                    title=tooltip,
                    size=size,
                    shape=shape,
                    color=color,
                    borderWidth=border_width,
                    borderWidthSelected=border_width + 2,
                    x=0,
                    y=0,
                    fixed=True  # Фиксируем в центре!
                )
            else:
                net.add_node(
                    node,
                    label=label,
                    title=tooltip,
                    size=size,
                    shape=shape,
                    color=color,
                    borderWidth=border_width,
                    borderWidthSelected=border_width + 2
                )
        
        # Add edges with curved support for bidirectional connections
        processed_edges = set()  # Track processed edge pairs
        
        for source, target in graph.edges():
            # Skip if reverse edge already processed
            edge_key = tuple(sorted([source, target]))
            if edge_key in processed_edges:
                continue
            processed_edges.add(edge_key)
            
            edge_data = graph.get_edge_data(source, target, default={})
            count = edge_data.get("count", 1)
            weight = edge_data.get("weight", 0)
            
            # Check if there's a reverse edge (bidirectional)
            has_reverse = graph.has_edge(target, source)
            
            # Get edge color based on transaction count
            color = self._get_edge_color(source, target, count, start_wallet)
            
            # Edge width (thin lines)
            width = 1.5
            
            # Create edge hover text
            hover_text = (
                f"From: {source[:12]}...\n"
                f"To: {target[:12]}...\n"
                f"Transactions: {count}\n"
                f"Total Volume: {weight:.2f}"
            )
            
            # Smooth type: curved for bidirectional, straight for unidirectional
            if has_reverse:
                # Bidirectional - use curved edges so they don't overlap
                smooth_config = {"type": "curvedCW", "roundness": 0.2}
            else:
                # Unidirectional - straight line
                smooth_config = {"type": "continuous"}
            
            net.add_edge(
                source,
                target,
                color=color,
                width=width,
                title=hover_text,
                smooth=smooth_config
            )
            
            # If bidirectional, add reverse edge with opposite curve
            if has_reverse:
                reverse_edge_data = graph.get_edge_data(target, source, default={})
                reverse_count = reverse_edge_data.get("count", 1)
                reverse_weight = reverse_edge_data.get("weight", 0)
                reverse_color = self._get_edge_color(target, source, reverse_count, start_wallet)
                
                reverse_hover_text = (
                    f"From: {target[:12]}...\n"
                    f"To: {source[:12]}...\n"
                    f"Transactions: {reverse_count}\n"
                    f"Total Volume: {reverse_weight:.2f}"
                )
                
                net.add_edge(
                    target,
                    source,
                    color=reverse_color,
                    width=width,
                    title=reverse_hover_text,
                    smooth={"type": "curvedCCW", "roundness": 0.2}  # Counter-clockwise curve
                )
        
        # Generate HTML
        html = net.generate_html()
        
        # Add Focus Mode JavaScript
        focus_mode_js = f"""
        <script type="text/javascript">
        (function() {{
            let selectedNode = null;
            const startWallet = '{start_wallet}';
            const originalEdgeColors = {{}};  // Store original colors
            
            // Store original edge colors on load
            network.on('stabilizationIterationsDone', function() {{
                const allEdges = network.body.data.edges.get();
                allEdges.forEach(edge => {{
                    originalEdgeColors[edge.id] = edge.color;
                }});
            }});
            
            // Wait for network to be ready
            network.on('click', function(params) {{
                if (params.nodes.length > 0) {{
                    // Node clicked
                    selectedNode = params.nodes[0];
                    applyFocusMode(selectedNode);
                }} else {{
                    // Canvas clicked (empty space)
                    selectedNode = null;
                    resetFocusMode();
                }}
            }});
            
            function hexToRgba(hex, alpha) {{
                // Convert hex color to rgba with alpha
                const r = parseInt(hex.slice(1, 3), 16);
                const g = parseInt(hex.slice(3, 5), 16);
                const b = parseInt(hex.slice(5, 7), 16);
                return `rgba(${{r}},${{g}},${{b}},${{alpha}})`;
            }}
            
            function applyFocusMode(clickedNode) {{
                const allNodes = network.body.data.nodes.get();
                const allEdges = network.body.data.edges.get();
                
                // Special case: if clicked on start wallet, show all its edges
                const isStartWalletClicked = (clickedNode === startWallet);
                
                // Update nodes
                allNodes.forEach(node => {{
                    if (node.id === clickedNode || node.id === startWallet) {{
                        // Keep selected node and start wallet bright
                        network.body.data.nodes.update({{
                            id: node.id,
                            opacity: 1.0,
                            font: {{ color: '#000000' }}
                        }});
                    }} else {{
                        // Dim other nodes
                        network.body.data.nodes.update({{
                            id: node.id,
                            opacity: 0.15,
                            font: {{ color: '#dddddd' }}
                        }});
                    }}
                }});
                
                // Update edges
                allEdges.forEach(edge => {{
                    let isRelevant;
                    
                    if (isStartWalletClicked) {{
                        // If start wallet clicked, show ALL its edges
                        isRelevant = (edge.from === startWallet || edge.to === startWallet);
                    }} else {{
                        // Otherwise, show ONLY edges between clickedNode ↔ startWallet
                        isRelevant = (edge.from === clickedNode && edge.to === startWallet) ||
                                    (edge.from === startWallet && edge.to === clickedNode);
                    }}
                    
                    if (isRelevant) {{
                        // Keep relevant edges bright and thick
                        network.body.data.edges.update({{
                            id: edge.id,
                            color: {{ opacity: 1.0 }},
                            width: 4,
                            hidden: false
                        }});
                    }} else {{
                        // Dim ALL other edges
                        network.body.data.edges.update({{
                            id: edge.id,
                            color: {{ opacity: 0.05 }},  // Very dim
                            width: 0.5,
                            hidden: false
                        }});
                    }}
                }});
            }}
            
            function resetFocusMode() {{
                const allNodes = network.body.data.nodes.get();
                const allEdges = network.body.data.edges.get();
                
                // Reset all nodes to original opacity
                allNodes.forEach(node => {{
                    network.body.data.nodes.update({{
                        id: node.id,
                        opacity: 1.0,
                        font: {{ color: '#000000' }}
                    }});
                }});
                
                // Reset all edges to original style
                allEdges.forEach(edge => {{
                    network.body.data.edges.update({{
                        id: edge.id,
                        color: {{ opacity: 1.0 }},
                        width: 1.5,
                        hidden: false
                    }});
                }});
            }}
        }})();
        </script>
        """
        
        # Inject JavaScript before closing </body> tag
        html = html.replace('</body>', focus_mode_js + '</body>')
        
        # Calculate wallet volumes for slider
        wallet_volumes = {}
        for node in graph.nodes():
            volume = 0
            # Sum all transactions between this node and start_wallet
            for tx in transactions:
                if (tx.get('from') == node and tx.get('to') == start_wallet) or \
                   (tx.get('from') == start_wallet and tx.get('to') == node):
                    volume += float(tx.get('amount', 0))
            wallet_volumes[node] = volume
        
        max_volume = max(wallet_volumes.values()) if wallet_volumes else 1000
        min_volume = min([v for v in wallet_volumes.values() if v > 0], default=0.01)
        
        # Add Volume Slider with Logarithmic/Linear toggle
        import math
        volume_slider_js = f"""
        <style>
        #volumeSliderContainer {{
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            z-index: 1000;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px 12px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            min-width: 90px;
        }}
        #volumeSlider {{
            writing-mode: bt-lr;
            -webkit-appearance: slider-vertical;
            width: 45px;
            height: 320px;
            margin: 10px auto;
            display: block;
            cursor: pointer;
        }}
        #volumeLabel {{
            font-size: 13px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 8px;
            color: #2c3e50;
        }}
        #volumeValue {{
            font-size: 15px;
            font-weight: bold;
            text-align: center;
            margin-top: 10px;
            color: #FF6B35;
            min-height: 20px;
        }}
        #volumeAsset {{
            font-size: 11px;
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 10px;
        }}
        #scaleToggle {{
            display: flex;
            justify-content: center;
            gap: 4px;
            margin-top: 10px;
        }}
        .scale-btn {{
            padding: 4px 8px;
            font-size: 10px;
            border: 1px solid #bdc3c7;
            background: white;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .scale-btn.active {{
            background: #3498db;
            color: white;
            border-color: #3498db;
        }}
        .scale-btn:hover {{
            background: #ecf0f1;
        }}
        .scale-btn.active:hover {{
            background: #2980b9;
        }}
        </style>
        
        <div id="volumeSliderContainer">
            <div id="volumeLabel">Min Volume</div>
            <input type="range" id="volumeSlider" min="0" max="100" value="0" step="1">
            <div id="volumeValue">0</div>
            <div id="volumeAsset">{selected_asset}</div>
            <div id="scaleToggle">
                <button class="scale-btn active" data-scale="quadratic">Quad</button>
                <button class="scale-btn" data-scale="log">Log</button>
                <button class="scale-btn" data-scale="linear">Linear</button>
            </div>
        </div>
        
        <script type="text/javascript">
        (function() {{
            const startWallet = '{start_wallet}';
            const walletVolumes = {wallet_volumes};
            const selectedAsset = '{selected_asset}';
            const maxVolume = {max_volume};
            const minVolume = {min_volume};
            
            const slider = document.getElementById('volumeSlider');
            const valueDisplay = document.getElementById('volumeValue');
            const scaleButtons = document.querySelectorAll('.scale-btn');
            
            let currentScale = 'quadratic'; // Default to QUADRATIC instead of log
            
            // Scale conversion functions
            function sliderToVolume(sliderValue) {{
                const t = sliderValue / 100; // 0 to 1
                
                if (currentScale === 'log') {{
                    // Logarithmic scale
                    if (t === 0) return 0;
                    const logMin = Math.log10(Math.max(minVolume, 0.01));
                    const logMax = Math.log10(maxVolume);
                    const logValue = logMin + t * (logMax - logMin);
                    return Math.pow(10, logValue);
                }} else if (currentScale === 'quadratic') {{
                    // Quadratic scale (x^2) - better distribution
                    return t * t * maxVolume;
                }} else {{
                    // Linear scale
                    return t * maxVolume;
                }}
            }}
            
            function volumeToSlider(volume) {{
                if (currentScale === 'log') {{
                    if (volume === 0) return 0;
                    const logMin = Math.log10(Math.max(minVolume, 0.01));
                    const logMax = Math.log10(maxVolume);
                    const logValue = Math.log10(volume);
                    return ((logValue - logMin) / (logMax - logMin)) * 100;
                }} else if (currentScale === 'quadratic') {{
                    // Quadratic scale inverse: sqrt(volume/maxVolume) * 100
                    return Math.sqrt(volume / maxVolume) * 100;
                }} else {{
                    return (volume / maxVolume) * 100;
                }}
            }}
            
            function formatVolume(volume) {{
                if (volume === 0) return '0';
                if (volume < 0.01) return volume.toFixed(4);
                if (volume < 1) return volume.toFixed(3);
                if (volume < 100) return volume.toFixed(2);
                if (volume < 10000) return volume.toFixed(1);
                return volume.toLocaleString('en-US', {{ maximumFractionDigits: 0 }});
            }}
            
            // Update display and apply filter
            function updateVolume() {{
                const sliderValue = parseFloat(slider.value);
                const minVolume = sliderToVolume(sliderValue);
                valueDisplay.textContent = formatVolume(minVolume);
                applyVolumeFilter(minVolume);
            }}
            
            // Slider input event
            slider.addEventListener('input', updateVolume);
            
            // Scale toggle
            scaleButtons.forEach(btn => {{
                btn.addEventListener('click', function() {{
                    const newScale = this.dataset.scale;
                    if (newScale === currentScale) return;
                    
                    // Get current volume
                    const currentVolume = sliderToVolume(parseFloat(slider.value));
                    
                    // Switch scale
                    currentScale = newScale;
                    scaleButtons.forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Update slider position to maintain same volume
                    slider.value = volumeToSlider(currentVolume);
                    updateVolume();
                }});
            }});
            
            function applyVolumeFilter(minVolume) {{
                const allNodes = network.body.data.nodes.get();
                const allEdges = network.body.data.edges.get();
                
                // Update nodes based on volume
                allNodes.forEach(node => {{
                    const nodeVolume = walletVolumes[node.id] || 0;
                    
                    if (node.id === startWallet || nodeVolume >= minVolume) {{
                        // Show nodes with volume >= threshold
                        network.body.data.nodes.update({{
                            id: node.id,
                            opacity: 1.0,
                            font: {{ color: '#000000' }}
                        }});
                    }} else {{
                        // Dim nodes with volume < threshold
                        network.body.data.nodes.update({{
                            id: node.id,
                            opacity: 0.1,
                            font: {{ color: '#eeeeee' }}
                        }});
                    }}
                }});
                
                // Update edges - dim edges to/from dimmed nodes
                allEdges.forEach(edge => {{
                    const fromVolume = walletVolumes[edge.from] || 0;
                    const toVolume = walletVolumes[edge.to] || 0;
                    
                    const fromVisible = edge.from === startWallet || fromVolume >= minVolume;
                    const toVisible = edge.to === startWallet || toVolume >= minVolume;
                    
                    if (fromVisible && toVisible) {{
                        // Show edge - BOTH nodes visible
                        network.body.data.edges.update({{
                            id: edge.id,
                            color: {{ opacity: 1.0 }},
                            width: 1.5,
                            hidden: false
                        }});
                    }} else {{
                        // Dim edge - at least one node is dimmed
                        network.body.data.edges.update({{
                            id: edge.id,
                            color: {{ opacity: 0.05 }},
                            width: 0.5,
                            hidden: false
                        }});
                    }}
                }});
            }}
            
            // Initialize
            updateVolume();
        }})();
        </script>
        """
        
        # Inject Volume Slider before closing </body> tag
        html = html.replace('</body>', volume_slider_js + '</body>')
        
        # Add tooltip styles (полупрозрачный фон)
        tooltip_styles = """
        <style>
        .vis-tooltip {
            background-color: rgba(255, 255, 255, 0.92) !important;
            border: 1px solid rgba(0, 0, 0, 0.2) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
            border-radius: 8px !important;
            padding: 12px !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            font-size: 13px !important;
            line-height: 1.6 !important;
            max-width: 400px !important;
            z-index: 9999 !important;
            pointer-events: none !important;
        }
        </style>
        """
        html = html.replace('</head>', tooltip_styles + '</head>')
        
        logger.info(f"Created interactive figure with {len(graph.nodes())} nodes and Focus Mode")
        return html
