"""
Main Streamlit application for Stellar Network Visualization.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import networkx as nx
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List, Optional
import sys
from pathlib import Path
import logging

# Configure DETAILED logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.api.stellar_client import StellarClient, StellarDataFetcher
from src.visualization.graph_builder import NetworkGraphBuilder
from src.visualization.graph_builder_enhanced import EnhancedNetworkGraphBuilder
from src.analysis.wallet_analyzer import WalletAnalyzer
from config.settings import settings

# Page configuration
st.set_page_config(
    page_title="Stellar Network Visualization",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    h1 {
        color: #1f77b4;
    }
    .stat-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# Кэшируемая функция для фетчинга данных
@st.cache_data(
    show_spinner=False,
    ttl=3600,  # 1 час - исторические данные не меняются быстро
    persist="disk",  # Сохраняем на диск между сессиями
    max_entries=50  # Максимум 50 разных комбинаций параметров
)
def fetch_wallet_network_cached(
    wallet_address: str,
    depth: int,
    max_wallets: int,
    strategy: str,
    asset_filter: tuple,  # tuple для hashable
    tx_type_filter: tuple,
    date_from_str: str,  # str для hashable
    date_to_str: str,
    direction_filter: tuple,
    min_amount: float,
    max_amount: float,
    max_pages: int
):
    """Кэшируемая обертка для fetch_wallet_network."""
    # Создаем новый fetcher для кэша
    client = StellarClient()
    fetcher = StellarDataFetcher(client)
    
    # Конвертируем обратно в нужные типы
    from datetime import datetime
    date_from = datetime.fromisoformat(date_from_str).date() if date_from_str else None
    date_to = datetime.fromisoformat(date_to_str).date() if date_to_str else None
    
    # Конвертируем tuple обратно в list или None
    asset_filter_list = list(asset_filter) if asset_filter else None
    tx_type_filter_list = list(tx_type_filter) if tx_type_filter else None
    direction_filter_list = list(direction_filter) if direction_filter else None
    
    # Выполняем фетчинг
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(
        fetcher.fetch_wallet_network(
            wallet_address,
            depth=depth,
            max_wallets=max_wallets,
            strategy=strategy,
            asset_filter=asset_filter_list,
            tx_type_filter=tx_type_filter_list,
            date_from=date_from,
            date_to=date_to,
            direction_filter=direction_filter_list,
            min_amount=min_amount,
            max_amount=max_amount,
            max_pages=max_pages  # ПЕРЕДАЕМ max_pages
        )
    )
    return data


class StellarVizApp:
    """Main Streamlit application class."""
    
    def __init__(self):
        """Initialize the application."""
        self.client = StellarClient()
        self.fetcher = StellarDataFetcher(self.client)
        self.graph_builder = NetworkGraphBuilder()
        self.enhanced_graph_builder = EnhancedNetworkGraphBuilder()
        self.wallet_analyzer = WalletAnalyzer()
        
        # Initialize session state
        if "network_data" not in st.session_state:
            st.session_state.network_data = None
        if "selected_wallet" not in st.session_state:
            st.session_state.selected_wallet = None
        if "graph_layout" not in st.session_state:
            st.session_state.graph_layout = "force"
        if "highlight_wallet" not in st.session_state:
            st.session_state.highlight_wallet = None
        if "center_wallet" not in st.session_state:
            st.session_state.center_wallet = None
        if "asset_filter" not in st.session_state:
            st.session_state.asset_filter = ["USDC"]
        if "tx_type_filter" not in st.session_state:
            st.session_state.tx_type_filter = ["All"]
        if "date_from" not in st.session_state:
            st.session_state.date_from = (datetime.now() - timedelta(days=365)).date()
        if "date_to" not in st.session_state:
            st.session_state.date_to = datetime.now().date()
        if "direction_filter" not in st.session_state:
            st.session_state.direction_filter = ["All"]
        if "min_amount" not in st.session_state:
            st.session_state.min_amount = None
        if "max_amount" not in st.session_state:
            st.session_state.max_amount = None
    
    def run(self):
        """Run the main application."""
        self.render_header()
        self.render_sidebar()
        
        if st.session_state.network_data:
            self.render_main_content()
        else:
            self.render_welcome()
    
    def render_header(self):
        """Render application header."""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🌟 Stellar Network Visualization")
            st.caption("Explore and analyze wallet connections in the Stellar blockchain")
    
    def render_sidebar(self):
        """Render sidebar with controls."""
        with st.sidebar:
            st.header("⚙️ Configuration")
            
            # Help/Documentation expander
            with st.expander("❓ Help & Guide", expanded=False):
                st.markdown("""
                ### 🎯 Quick Start
                
                **1. Enter Wallet** → Stellar address (G...)  
                **2. Set Parameters** → Depth: 2, Max: 50  
                **3. Choose Filters** → Currency, Date, etc.  
                **4. Click "Fetch"** → Wait 5-10 seconds
                
                ### 📋 Filters Explained
                
                **Assets (Currency)**
                - `XLM` = Lumens (native)
                - `USDC` = USD Coin stablecoin
                - `EURC` = EUR Coin stablecoin
                - `yUSDC` = Yield USDC
                - `SSLX` = SSL Exchange token (sslx.sl8.online)
                
                **Transaction Types**
                - `payment` = Standard transfer
                - `create_account` = New wallet
                - `path_payment` = Cross-currency
                
                **Direction** 🆕
                - `Sent` = FROM main wallet
                - `Received` = TO main wallet
                - `All` = Both directions
                
                **Amount** 🆕
                - Set min/max to filter by value
                - Remove dust (min=0.1)
                - Find whales (min=1000+)
                
                **Min Transactions** 🆕
                - Hide low-activity wallets
                - Set to 1 to hide single transactions
                - Set to 5+ to see only frequent partners
                
                ### 🎨 Visualization
                
                **Layouts**
                - Force = Natural physics
                - Circular = Ring arrangement  
                - Hierarchical = Tree structure
                - Spectral = Math-based
                
                **Node Size**
                - Connections = # of links
                - Transactions = Activity level
                - Volume = Total value
                
                **Interactivity** 🆕
                - 🔦 Highlight = Focus on one wallet
                - 🎯 Center = Recenter view
                - 🖱️ Hover = Detailed stats
                
                💡 **Pro Tip**: Use filters to remove noise and focus on important flows!
                """)
            
            st.divider()
            
            # Wallet input
            st.subheader("🔍 Explore Wallet")
            wallet_address = st.text_input(
                "Enter Stellar wallet address:",
                value="GAYFS6KPNCE5II2YGJMONCBDJ2UF5WQBUQKNBDAHXKOURI466QPAQ3JZ",
                placeholder="GAYFS6KPNCE5II2YGJMONCBDJ2UF5WQBUQKNBDAHXKOURI466QPAQ3JZ"
            )
            
            # Exploration parameters - PERFECTLY ALIGNED
            st.markdown("**Network Parameters:**")
            col1, col2 = st.columns(2)
            with col1:
                depth = st.number_input(
                    "Depth",
                    min_value=1,
                    max_value=5,
                    value=2,
                    help="Exploration depth: Number of hops from starting wallet. Depth=2 recommended for good overview.",
                    key="depth_input"
                )
            with col2:
                max_wallets = st.number_input(
                    "Max Wallets",
                    min_value=10,
                    max_value=200,
                    value=100,
                    step=10,
                    help="Maximum number of wallets to analyze. More wallets = better network view.",
                    key="max_wallets_input"
                )
            
            # Strategy selection
            strategy = st.selectbox(
                "Selection strategy:",
                options=["most_active", "breadth_first"],
                format_func=lambda x: {
                    "most_active": "🎯 Most Active (Recommended)",
                    "breadth_first": "🌐 Breadth First"
                }[x],
                help="Most Active: Prioritize wallets with highest transaction count"
            )
            
            # Max pages limit
            st.markdown("**📊 Data Collection Limit:**")
            max_pages_options = {
                "⚡ Fast (~2K tx)": 10,
                "⚙️ Normal (~5K tx)": 25,
                "📈 Extended (~10K tx)": 50,
                "🔥 Full (~20K tx)": 100,
                "♾️ Unlimited": 1000
            }
            max_pages_choice = st.selectbox(
                "Max transactions per wallet:",
                options=list(max_pages_options.keys()),
                index=1,  # Default: Normal
                help="Higher limits = more complete data but slower. For most wallets, Normal is enough."
            )
            max_pages = max_pages_options[max_pages_choice]
            st.session_state.max_pages = max_pages
            
            if "Unlimited" in max_pages_choice:
                st.error("⚠️ May take 10+ minutes for very active wallets!")
            # Performance warnings removed - user feedback
            
            # Filters
            st.subheader("🎯 Filters")
            
            # Asset filter - ONLY ONE asset selection allowed!
            asset_filter = st.selectbox(
                "Filter by asset:",
                options=["XLM", "USDC", "EURC", "yUSDC", "SSLX", "All"],
                index=1,  # ДЕФОЛТ: USDC (индекс 1)
                help="Filter transactions by asset type. Select 'All' to include all assets. SSLX = sslx.sl8.online"
            )
            # Преобразуем в список для совместимости с остальным кодом
            st.session_state.asset_filter = [asset_filter]
            
            # Transaction type filter
            tx_type_filter = st.multiselect(
                "Transaction types:",
                options=["payment", "create_account", "path_payment", "All"],
                default=["All"],
                help="Filter by transaction type. Select 'All' to include all types."
            )
            st.session_state.tx_type_filter = tx_type_filter
            
            # Date range filter
            use_date_filter = st.checkbox("Enable date filter", value=True)  # ВКЛЮЧЕНО ПО УМОЛЧАНИЮ
            if use_date_filter:
                date_from = st.date_input(
                    "From date:",
                    value=datetime.now() - timedelta(days=365)  # ГОД НАЗАД
                )
                date_to = st.date_input(
                    "To date:",
                    value=datetime.now()
                )
                st.session_state.date_from = date_from
                st.session_state.date_to = date_to
            else:
                st.session_state.date_from = None
                st.session_state.date_to = None
            
            # Direction filter (Stage 2)
            direction_filter = st.multiselect(
                "Transaction direction:",
                options=["Sent", "Received", "All"],
                default=["All"],
                help="Filter by transaction direction: Sent (outgoing), Received (incoming), or All"
            )
            st.session_state.direction_filter = direction_filter
            
            # Amount filter (Stage 2)
            use_amount_filter = st.checkbox("Enable amount filter")
            if use_amount_filter:
                col1, col2 = st.columns(2)
                with col1:
                    min_amount = st.number_input(
                        "Min amount:",
                        min_value=0.0,
                        value=0.0,
                        step=10.0,
                        help="Minimum transaction amount"
                    )
                    st.session_state.min_amount = min_amount
                with col2:
                    max_amount = st.number_input(
                        "Max amount:",
                        min_value=0.0,
                        value=1000000.0,
                        step=100.0,
                        help="Maximum transaction amount (0 = no limit)"
                    )
                    st.session_state.max_amount = max_amount if max_amount > 0 else None
            else:
                st.session_state.min_amount = None
                st.session_state.max_amount = None
            
            # Min transaction count filter (NEW)
            st.markdown("**💡 Transaction Frequency Filter:**")
            min_tx_count = st.number_input(
                "Min transactions between wallets:",
                min_value=0,
                max_value=100,
                value=0,
                step=1,
                help="Hide wallets with fewer than X transactions with the main wallet. Use to remove low-activity connections."
            )
            st.session_state.min_tx_count = min_tx_count
            
            if min_tx_count > 0:
                st.info(f"ℹ️ Will hide wallets with ≤{min_tx_count} transactions")
            
            # Visualization settings
            st.subheader("🎨 Visualization")
            
            layout_type = st.selectbox(
                "Graph layout:",
                options=["force", "circular", "hierarchical", "spectral"],
                index=0
            )
            st.session_state.graph_layout = layout_type
            
            show_labels = st.checkbox("Show wallet labels", value=True)
            node_size_metric = st.selectbox(
                "Node size represents:",
                options=["Transaction count", "Total volume", "Unique connections", "Equal size"],
                index=0
            )
            
            # Fetch data button
            st.divider()
            
            # Action buttons - в 2 ряда
            col_reset, col_cache = st.columns(2)
            with col_reset:
                if st.button("🔄 Reset Filters", help="Reset all filters to default", width="stretch"):
                    st.session_state.asset_filter = ["USDC"]
                    st.session_state.tx_type_filter = ["All"]
                    st.session_state.direction_filter = ["All"]
                    st.session_state.date_from = (datetime.now() - timedelta(days=365)).date()
                    st.session_state.date_to = datetime.now().date()
                    st.session_state.min_amount = None
                    st.session_state.max_amount = None
                    st.session_state.min_tx_count = 0  # NEW
                    st.rerun()
            
            with col_cache:
                if st.button("🗑️ Clear Cache", help="Clear cached data (force refresh)", width="stretch"):
                    fetch_wallet_network_cached.clear()
                    st.success("✅ Cache cleared!")
                    st.rerun()
            
            # Fetch button отдельно
            if st.button("🚀 Fetch & Analyze", type="primary", width="stretch"):
                if wallet_address and len(wallet_address) == 56 and wallet_address.startswith("G"):
                    max_pages = st.session_state.get("max_pages", 25)  # Default: Normal
                    self.fetch_network_data(wallet_address, depth, max_wallets, strategy, max_pages)
                else:
                    st.error("Please enter a valid Stellar wallet address (56 characters starting with 'G')")
            
            # Network selection (for demo)
            st.divider()
            network_type = st.radio(
                "Network:",
                options=["Mainnet", "Testnet"],
                index=1 if settings.USE_TESTNET else 0
            )
            
            if network_type == "Testnet" and not settings.USE_TESTNET:
                settings.USE_TESTNET = True
                self.client = StellarClient()
                self.fetcher = StellarDataFetcher(self.client)
    
    def render_welcome(self):
        """Render welcome screen when no data is loaded."""
        st.markdown("""
        ## Welcome to Stellar Network Visualization! 👋
        
        This tool allows you to:
        - 🔍 **Explore** wallet connections in the Stellar network
        - 📊 **Analyze** transaction patterns and relationships
        - 🎨 **Visualize** the network graph interactively
        - 📈 **Track** asset flows between wallets
        
        ### Getting Started
        1. Enter a Stellar wallet address in the sidebar
        2. Configure exploration parameters
        3. Click "Fetch & Analyze" to load the network
        4. Interact with the visualization to explore connections
        
        ### Example Wallets (Testnet)
        - `GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN7` - Friendbot (faucet)
        - `GA2C5RFPE6GCKMY3US5PAB6UZLKIGSPIUKSLRB6Q723BM2OARMDUYEJ5` - Example exchange
        
        ### Tips
        - 🎯 Start with depth=2 and max_wallets=50 for optimal performance
        - 🔍 Click on nodes in the graph to center the view on that wallet
        - 📊 Hover over nodes and edges to see detailed statistics
        """)
        
        # Sample visualization
        with st.expander("📸 View Sample Visualization"):
            self.render_sample_graph()
    
    def render_main_content(self):
        """Render main content area with visualization and stats."""
        data = st.session_state.network_data
        
        # Show active filters if any
        active_filters = []
        asset_filter = st.session_state.get("asset_filter", ["All"])
        tx_type_filter = st.session_state.get("tx_type_filter", ["All"])
        date_from = st.session_state.get("date_from")
        date_to = st.session_state.get("date_to")
        
        if asset_filter and "All" not in asset_filter:
            active_filters.append(f"**Assets**: {', '.join(asset_filter)}")
        if tx_type_filter and "All" not in tx_type_filter:
            active_filters.append(f"**Types**: {', '.join(tx_type_filter)}")
        if date_from or date_to:
            date_str = f"{date_from or 'start'} to {date_to or 'end'}"
            active_filters.append(f"**Date range**: {date_str}")
        
        if active_filters:
            st.info(f"🎯 **Active Filters**: {' | '.join(active_filters)}")
        
        # Stats row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Wallets", data["stats"]["total_wallets"])
        with col2:
            st.metric("Total Transactions", data["stats"]["total_transactions"])
        with col3:
            total_volume = sum(
                float(tx.get("amount", 0)) 
                for tx in data["transactions"]
            )
            st.metric("Total Volume", f"{total_volume:,.2f} XLM")
        with col4:
            st.metric("Network Depth", data["stats"]["depth_explored"])
        
        # Main visualization
        st.subheader("🌐 Network Graph")
        
        # Interactive controls
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            # Wallet selector for highlighting
            wallet_options = ["None"] + list(data["wallets"].keys())
            highlight_idx = 0
            if st.session_state.highlight_wallet in wallet_options:
                highlight_idx = wallet_options.index(st.session_state.highlight_wallet)
            
            selected_highlight = st.selectbox(
                "🔍 Highlight wallet connections:",
                options=wallet_options,
                index=highlight_idx,
                format_func=lambda x: "None (show all)" if x == "None" else f"{x[:8]}...{x[-8:]}",
                help="Show only connections for selected wallet"
            )
            
            if selected_highlight != "None":
                st.session_state.highlight_wallet = selected_highlight
            else:
                st.session_state.highlight_wallet = None
        
        with col2:
            # Wallet selector for centering
            center_options = ["None"] + list(data["wallets"].keys())
            center_idx = 0
            if st.session_state.center_wallet in center_options:
                center_idx = center_options.index(st.session_state.center_wallet)
            
            selected_center = st.selectbox(
                "🎯 Center graph on wallet:",
                options=center_options,
                index=center_idx,
                format_func=lambda x: "Default" if x == "None" else f"{x[:8]}...{x[-8:]}",
                help="Center the graph layout on this wallet"
            )
            
            if selected_center != "None":
                st.session_state.center_wallet = selected_center
            else:
                st.session_state.center_wallet = None
        
        with col3:
            # Reset button
            if st.button("🔄 Reset View", help="Reset all filters and centering"):
                st.session_state.highlight_wallet = None
                st.session_state.center_wallet = None
                st.rerun()
        
        with col4:
            # Info button
            with st.popover("ℹ️ Help"):
                st.markdown("""
                **How to interact:**
                - **Hover** over nodes to see details
                - **Select** a wallet to highlight its connections
                - **Center** the graph on any wallet
                - **Click** "Reset View" to show all connections
                
                **Node colors:**
                - 🔴 Red: Centered wallet
                - 🟣 Purple: Highlighted wallet
                - 🟢 Teal: Connected to highlighted
                - 🔵 Blue: Other wallets (by degree)
                """)
        
        # Display graph
        if not data.get("wallets") or not data.get("transactions"):
            st.error("⚠️ No data to display. The network might be empty or filters are too restrictive.")
            st.info("💡 Try removing some filters or changing the wallet address.")
            return
        
        # Debug info - EXPANDED for data completeness check
        with st.expander("🔍 Debug Info & Data Completeness Check", expanded=False):
            st.markdown("### 📊 Current Data")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Wallets", len(data['wallets']))
            with col2:
                st.metric("Transactions", len(data['transactions']))
            with col3:
                st.metric("Layout", st.session_state.graph_layout)
            
            st.markdown("### 🎯 Selected Filters")
            st.write(f"**Asset:** {st.session_state.asset_filter}")
            st.write(f"**Transaction types:** {st.session_state.tx_type_filter}")
            st.write(f"**Date range:** {st.session_state.get('date_from')} to {st.session_state.get('date_to')}")
            st.write(f"**Direction:** {st.session_state.get('direction_filter', ['All'])}")
            st.write(f"**Amount range:** {st.session_state.get('min_amount', 'N/A')} - {st.session_state.get('max_amount', 'N/A')}")
            st.write(f"**Min TX count:** {st.session_state.get('min_tx_count', 0)}")
            st.write(f"**Highlight:** {st.session_state.highlight_wallet}")
            st.write(f"**Center:** {st.session_state.center_wallet}")
            
            st.markdown("### 🔍 Data Completeness Check")
            
            # Анализ транзакций
            start_wallet = st.session_state.get('selected_wallet')
            if start_wallet:
                st.write(f"**Start Wallet:** `{start_wallet[:12]}...`")
                
                # Транзакции со стартовым кошельком
                start_wallet_txs = [
                    tx for tx in data['transactions']
                    if tx.get('from') == start_wallet or tx.get('to') == start_wallet
                ]
                
                st.write(f"**Transactions with start wallet:** {len(start_wallet_txs)}")
                
                # Разбивка по направлению
                sent_from_start = [tx for tx in start_wallet_txs if tx.get('from') == start_wallet]
                received_by_start = [tx for tx in start_wallet_txs if tx.get('to') == start_wallet]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📤 Sent", len(sent_from_start))
                    if sent_from_start:
                        sent_total = sum(float(tx.get('amount', 0)) for tx in sent_from_start)
                        st.caption(f"Total: {sent_total:,.2f}")
                with col2:
                    st.metric("📥 Received", len(received_by_start))
                    if received_by_start:
                        received_total = sum(float(tx.get('amount', 0)) for tx in received_by_start)
                        st.caption(f"Total: {received_total:,.2f}")
                
                # Уникальные кошельки в транзакциях
                unique_wallets_in_txs = set()
                for tx in data['transactions']:
                    if tx.get('from'):
                        unique_wallets_in_txs.add(tx.get('from'))
                    if tx.get('to'):
                        unique_wallets_in_txs.add(tx.get('to'))
                
                st.write(f"**Unique wallets in transactions:** {len(unique_wallets_in_txs)}")
                st.write(f"**Wallets in data['wallets']:** {len(data['wallets'])}")
                
                # Проверка несоответствий
                wallets_in_txs_not_in_data = unique_wallets_in_txs - set(data['wallets'].keys())
                wallets_in_data_not_in_txs = set(data['wallets'].keys()) - unique_wallets_in_txs
                
                if wallets_in_txs_not_in_data:
                    st.warning(f"⚠️ {len(wallets_in_txs_not_in_data)} wallets appear in transactions but not in wallets data")
                    with st.expander("Show missing wallets"):
                        for w in list(wallets_in_txs_not_in_data)[:10]:
                            st.text(f"{w[:12]}...")
                
                if wallets_in_data_not_in_txs:
                    st.info(f"ℹ️ {len(wallets_in_data_not_in_txs)} wallets in data but have no transactions (filtered out)")
            
            st.markdown("### 📈 Transaction Statistics")
            
            # Разбивка по валютам
            asset_counts = {}
            for tx in data['transactions']:
                asset = tx.get('asset_code', 'XLM')
                asset_counts[asset] = asset_counts.get(asset, 0) + 1
            
            st.write("**Transactions by asset:**")
            for asset, count in sorted(asset_counts.items(), key=lambda x: x[1], reverse=True):
                st.text(f"  {asset}: {count}")
            
            # Разбивка по типам
            type_counts = {}
            for tx in data['transactions']:
                tx_type = tx.get('type', 'unknown')
                type_counts[tx_type] = type_counts.get(tx_type, 0) + 1
            
            st.write("**Transactions by type:**")
            for tx_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                st.text(f"  {tx_type}: {count}")
            
            # Временной диапазон реальных данных
            dates = []
            for tx in data['transactions']:
                created_at = tx.get('created_at')
                if created_at:
                    if isinstance(created_at, str):
                        try:
                            from datetime import datetime
                            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            dates.append(date_obj)
                        except:
                            pass
                    else:
                        dates.append(created_at)
            
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                st.write(f"**Actual date range in data:** {min_date.date()} to {max_date.date()}")
            
            
            st.markdown("### ⚙️ Filtering Pipeline Statistics")
            
            # Показываем статистику фильтрации если она есть
            if 'filtering_stats' in data.get('stats', {}):
                fs = data['stats']['filtering_stats']
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📥 Initial", fs['initial_transactions'], help="Transactions collected from API")
                with col2:
                    st.metric("🔽 After Top Wallets", fs['after_top_wallets_filter'], 
                             delta=fs['after_top_wallets_filter'] - fs['initial_transactions'],
                             help="After selecting top N most active wallets")
                with col3:
                    st.metric("✅ Final", fs['final_transactions'],
                             delta=fs['final_transactions'] - fs['initial_transactions'],
                             help="After all filters (asset, date, amount, etc)")
                with col4:
                    loss_percent = (fs['transactions_lost'] / fs['initial_transactions'] * 100) if fs['initial_transactions'] > 0 else 0
                    st.metric("❌ Lost", fs['transactions_lost'],
                             delta=f"-{loss_percent:.1f}%",
                             help="Total transactions filtered out")
                
                if fs['transactions_lost'] > fs['initial_transactions'] * 0.5:
                    st.error(f"⚠️ **Warning:** More than 50% of transactions were filtered out! ({loss_percent:.1f}%)")
                    st.markdown("""
                    **Possible causes:**
                    - Too restrictive filters (asset, amount, direction)
                    - Date range too narrow
                    - Most transactions don't match filter criteria
                    
                    **Try:**
                    - Widening date range
                    - Removing amount/direction filters
                    - Selecting "All" for asset filter
                    """)
                elif fs['transactions_lost'] > 0:
                    st.info(f"ℹ️ {fs['transactions_lost']} transactions ({loss_percent:.1f}%) were filtered out - this is normal if you have active filters")
            else:
                st.warning("No filtering statistics available")
            
            st.markdown("### 💡 Recommendations")
            if len(data['transactions']) < 50:
                st.warning("⚠️ Low transaction count. Consider:")
                st.markdown("""
                - Increasing 'Max transactions per wallet' in sidebar
                - Widening date range filter
                - Removing restrictive filters (amount, direction)
                - Checking if the wallet has more activity
                """)
        
        graph_fig = self.create_network_graph(data)
        
        if graph_fig is None:
            st.error("❌ Failed to create graph. Please try again.")
            return
        
        # Use Streamlit's plotly_events for click handling
        # Note: This requires streamlit-plotly-events package for full click support
        # For now, we use the standard plotly_chart
        st.plotly_chart(graph_fig, width="stretch", key="network_graph")
        
        # ========================
        # EDGE COLOR LEGEND (Collapsible)
        # ========================
        with st.expander("📊 **Edge Color Legend** - Click to see what colors mean", expanded=False):
            st.markdown("### Connection Line Colors")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🟠 Start Wallet Links:**")
                st.markdown("""
                <div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px;'>
                <span style='color:#FF4500; font-size:20px;'>■</span> 10+ transactions<br>
                <span style='color:#0066FF; font-size:20px;'>■</span> 5-9 transactions (blue)<br>
                <span style='color:#FFA500; font-size:20px;'>■</span> 2-4 transactions<br>
                <span style='color:#00CC66; font-size:20px;'>■</span> 1 transaction (green)
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("**⚫ Other Wallet Links:**")
                st.markdown("""
                <div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px;'>
                <span style='color:#666666; font-size:20px;'>■</span> 10+ transactions<br>
                <span style='color:#0066FF; font-size:20px;'>■</span> 5-9 transactions (blue)<br>
                <span style='color:#AAAAAA; font-size:20px;'>■</span> 2-4 transactions<br>
                <span style='color:#00CC66; font-size:20px;'>■</span> 1 transaction (green)
                </div>
                """, unsafe_allow_html=True)
            
            st.info("""
            💡 **Tip:** 
            - 🔵 **Blue** = 5-9 transactions
            - 🟢 **Green** = 1 transaction
            - **Darker colors** = more transactions between wallets
            """)
        
        # ========================
        # ПУНКТЫ 3, 9, 10: DETAILED WALLET INFO PANEL
        # ========================
        # Show detailed wallet info for highlighted wallet
        if st.session_state.highlight_wallet:
            selected_wallet = st.session_state.highlight_wallet
            wallet_data = data["wallets"].get(selected_wallet, {})
            
            st.markdown("---")
            st.markdown("### 🔍 Selected Wallet Details")
            
            with st.expander("📋 **Wallet Information** (Click to expand/collapse)", expanded=True):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Full Address:**")
                    st.code(selected_wallet, language=None)
                    st.caption("💡 Click inside the box to select and copy the address")
                
                with col2:
                    is_start = (selected_wallet == st.session_state.get('selected_wallet'))
                    if is_start:
                        st.markdown("🎯 **START WALLET**")
                
                # Stats
                balance = wallet_data.get("balance_xlm", 0)
                total_tx = wallet_data.get("transaction_count", 0)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💰 Balance", f"{balance:,.4f} XLM")
                with col2:
                    st.metric("📊 Total Transactions", total_tx)
                with col3:
                    connections = wallet_data.get("unique_counterparties", 0)
                    st.metric("🔗 Connections", connections)
                
                # Transaction breakdown by direction
                st.markdown("#### 💸 Transaction Breakdown")
                
                # Filter transactions for this wallet
                wallet_txs = [
                    tx for tx in data["transactions"]
                    if tx.get("from") == selected_wallet or tx.get("to") == selected_wallet
                ]
                
                sent_txs = [tx for tx in wallet_txs if tx.get("from") == selected_wallet]
                received_txs = [tx for tx in wallet_txs if tx.get("to") == selected_wallet]
                
                # Get selected asset for display
                selected_asset = st.session_state.asset_filter[0] if st.session_state.asset_filter else "XLM"
                if selected_asset == "All":
                    selected_asset = "XLM"
                
                # Calculate totals
                sent_total = sum(float(tx.get("amount", 0)) for tx in sent_txs)
                received_total = sum(float(tx.get("amount", 0)) for tx in received_txs)
                net_flow = received_total - sent_total
                net_emoji = "📈" if net_flow > 0 else "📉" if net_flow < 0 else "➖"
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "📤 Sent (Outgoing)", 
                        f"{sent_total:,.2f} {selected_asset}",
                        f"{len(sent_txs)} transactions"
                    )
                with col2:
                    st.metric(
                        "📥 Received (Incoming)", 
                        f"{received_total:,.2f} {selected_asset}",
                        f"{len(received_txs)} transactions"
                    )
                with col3:
                    st.metric(
                        f"{net_emoji} Net Flow", 
                        f"{abs(net_flow):,.2f} {selected_asset}",
                        "Positive" if net_flow > 0 else "Negative" if net_flow < 0 else "Neutral"
                    )
                
                # Detailed transaction lists with dates and amounts
                st.markdown("#### 📜 Detailed Transaction History")
                
                tab_sent, tab_received = st.tabs(["📤 Sent Transactions", "📥 Received Transactions"])
                
                with tab_sent:
                    if sent_txs:
                        st.caption(f"Showing {len(sent_txs)} outgoing transactions")
                        for i, tx in enumerate(sorted(sent_txs, key=lambda x: x.get("created_at", ""), reverse=True)[:20]):
                            with st.container():
                                col1, col2, col3 = st.columns([2, 2, 1])
                                with col1:
                                    tx_date = tx.get("created_at", "Unknown")[:19]
                                    st.text(f"📅 {tx_date}")
                                with col2:
                                    to_wallet = tx.get("to", "Unknown")
                                    st.text(f"→ {to_wallet[:12]}...")
                                with col3:
                                    amount = float(tx.get("amount", 0))
                                    asset = tx.get("asset_code", "XLM")
                                    st.text(f"{amount:,.2f} {asset}")
                                if i < len(sent_txs) - 1:
                                    st.divider()
                        if len(sent_txs) > 20:
                            st.info(f"💡 Showing first 20 of {len(sent_txs)} transactions")
                    else:
                        st.info("No sent transactions found")
                
                with tab_received:
                    if received_txs:
                        st.caption(f"Showing {len(received_txs)} incoming transactions")
                        for i, tx in enumerate(sorted(received_txs, key=lambda x: x.get("created_at", ""), reverse=True)[:20]):
                            with st.container():
                                col1, col2, col3 = st.columns([2, 2, 1])
                                with col1:
                                    tx_date = tx.get("created_at", "Unknown")[:19]
                                    st.text(f"📅 {tx_date}")
                                with col2:
                                    from_wallet = tx.get("from", "Unknown")
                                    st.text(f"← {from_wallet[:12]}...")
                                with col3:
                                    amount = float(tx.get("amount", 0))
                                    asset = tx.get("asset_code", "XLM")
                                    st.text(f"{amount:,.2f} {asset}")
                                if i < len(received_txs) - 1:
                                    st.divider()
                        if len(received_txs) > 20:
                            st.info(f"💡 Showing first 20 of {len(received_txs)} transactions")
                    else:
                        st.info("No received transactions found")
        
        # Add tip below graph
        st.info("💡 **Tip:** Select a wallet in the 'Highlight wallet' dropdown above to see detailed information.")
        
        # Detailed views
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Wallet Analysis", 
            "💸 Transactions", 
            "📈 Metrics", 
            "🔍 Details",
            "🔎 Path Finder"  # ← NEW TAB
        ])
        
        with tab1:
            self.render_wallet_analysis(data)
        
        with tab2:
            self.render_transactions_table(data)
        
        with tab3:
            self.render_network_metrics(data)
        
        with tab4:
            self.render_raw_data(data)
        
        with tab5:
            self.render_path_finder(data)  # ← NEW: Path Finder tab
    
    def fetch_network_data(self, wallet_address: str, depth: int, max_wallets: int, strategy: str = "most_active", max_pages: int = 25):
        """Fetch network data from Stellar with filters."""
        # Get filters from session state
        asset_filter = st.session_state.get("asset_filter", ["All"])
        tx_type_filter = st.session_state.get("tx_type_filter", ["All"])
        date_from = st.session_state.get("date_from")
        date_to = st.session_state.get("date_to")
        direction_filter = st.session_state.get("direction_filter", ["All"])
        min_amount = st.session_state.get("min_amount")
        max_amount = st.session_state.get("max_amount")
        
        # Build filter description for user
        filter_desc = []
        if asset_filter and "All" not in asset_filter:
            filter_desc.append(f"Assets: {', '.join(asset_filter)}")
        if tx_type_filter and "All" not in tx_type_filter:
            filter_desc.append(f"Types: {', '.join(tx_type_filter)}")
        if date_from or date_to:
            filter_desc.append("Date range applied")
        if direction_filter and "All" not in direction_filter:
            filter_desc.append(f"Direction: {', '.join(direction_filter)}")
        if min_amount is not None or max_amount is not None:
            if min_amount and max_amount:
                filter_desc.append(f"Amount: {min_amount}-{max_amount}")
            elif min_amount:
                filter_desc.append(f"Amount: ≥{min_amount}")
            elif max_amount:
                filter_desc.append(f"Amount: ≤{max_amount}")
        
        filter_text = f" (Filters: {', '.join(filter_desc)})" if filter_desc else ""
        
        # Показываем что именно загружаем
        status_placeholder = st.empty()
        status_placeholder.info(f"🔍 Fetching for wallet {wallet_address[:8]}... {filter_text}")
        
        with st.spinner(f"Loading network data..."):
            try:
                # Подготовка параметров для кэшируемой функции
                # Конвертируем в hashable типы
                asset_filter_tuple = tuple(asset_filter) if asset_filter and "All" not in asset_filter else ()
                tx_type_filter_tuple = tuple(tx_type_filter) if tx_type_filter and "All" not in tx_type_filter else ()
                direction_filter_tuple = tuple(direction_filter) if direction_filter and "All" not in direction_filter else ()
                
                date_from_str = date_from.isoformat() if date_from else ""
                date_to_str = date_to.isoformat() if date_to else ""
                
                # Вызываем КЭШИРУЕМУЮ функцию
                data = fetch_wallet_network_cached(
                    wallet_address,
                    depth,
                    max_wallets,
                    strategy,
                    asset_filter_tuple,
                    tx_type_filter_tuple,
                    date_from_str,
                    date_to_str,
                    direction_filter_tuple,
                    min_amount if min_amount is not None else -1.0,  # -1.0 = не задано
                    max_amount if max_amount is not None else -1.0,  # -1.0 = не задано
                    max_pages  # ПЕРЕДАЕМ max_pages
                )
                
                st.session_state.network_data = data
                st.session_state.selected_wallet = wallet_address
                
                # Очищаем status placeholder
                status_placeholder.empty()
                
                # Show statistics with filter info
                discovered = data['stats'].get('wallets_discovered', 0)
                tx_count = len(data['transactions'])
                
                success_msg = f"✅ Loaded {len(data['wallets'])} wallets and {tx_count} transactions"
                if filter_desc:
                    success_msg += f"\n🎯 Active filters: {', '.join(filter_desc)}"
                
                if discovered > max_wallets:
                    success_msg = f"✅ Found {discovered} wallets, selected top {len(data['wallets'])} most active. " + success_msg
                
                st.success(success_msg)
                st.rerun()
                
            except Exception as e:
                status_placeholder.empty()
                st.error(f"❌ Error fetching data: {str(e)}")
                logger.error(f"Error in fetch_network_data: {e}", exc_info=True)
    
    def create_network_graph(self, data: Dict) -> go.Figure:
        """Create interactive network graph visualization with hover and click support."""
        try:
            logger.info(f"Creating graph with {len(data['wallets'])} wallets and {len(data['transactions'])} transactions")
            
            # Применяем фильтр min_tx_count (если установлен)
            min_tx_count = st.session_state.get('min_tx_count', 0)
            if min_tx_count > 0:
                start_wallet = st.session_state.get('selected_wallet')
                if start_wallet:
                    # Считаем количество транзакций между каждым кошельком и start_wallet
                    wallet_tx_counts = {}
                    for tx in data['transactions']:
                        from_wallet = tx.get('from')
                        to_wallet = tx.get('to')
                        
                        # Считаем транзакции с start_wallet
                        if from_wallet == start_wallet and to_wallet:
                            wallet_tx_counts[to_wallet] = wallet_tx_counts.get(to_wallet, 0) + 1
                        elif to_wallet == start_wallet and from_wallet:
                            wallet_tx_counts[from_wallet] = wallet_tx_counts.get(from_wallet, 0) + 1
                    
                    # Фильтруем кошельки
                    filtered_wallets = {
                        w_id: w_data 
                        for w_id, w_data in data['wallets'].items() 
                        if w_id == start_wallet or wallet_tx_counts.get(w_id, 0) > min_tx_count
                    }
                    
                    # Фильтруем транзакции (только между оставшимися кошельками)
                    filtered_transactions = [
                        tx for tx in data['transactions']
                        if tx.get('from') in filtered_wallets and tx.get('to') in filtered_wallets
                    ]
                    
                    removed_wallets = len(data['wallets']) - len(filtered_wallets)
                    removed_tx = len(data['transactions']) - len(filtered_transactions)
                    
                    logger.info(f"Min TX count filter ({min_tx_count}): Removed {removed_wallets} wallets and {removed_tx} transactions")
                    
                    if removed_wallets > 0:
                        st.info(f"💡 Filtered out {removed_wallets} wallets with ≤{min_tx_count} transactions")
                    
                    # Обновляем data
                    data = {
                        'wallets': filtered_wallets,
                        'transactions': filtered_transactions,
                        'stats': data['stats']
                    }
                    
                    logger.info(f"After min_tx_count filter: {len(filtered_wallets)} wallets, {len(filtered_transactions)} transactions")
            
            
            # Валидация: проверяем что все ID кошельков корректные (56 символов)
            invalid_wallets = [w for w in data['wallets'].keys() if len(w) != 56]
            if invalid_wallets:
                logger.error(f"Found {len(invalid_wallets)} invalid wallet IDs: {invalid_wallets[:3]}")
                st.error(f"❌ Data contains invalid wallet IDs. Please check the data source.")
                return None
            
            # Build network graph using enhanced builder
            G = self.enhanced_graph_builder.build_graph(
                data["wallets"],
                data["transactions"],
                directed=True
            )
            
            logger.info(f"Graph built: {len(G.nodes())} nodes, {len(G.edges())} edges")
            
            # ИСПРАВЛЕНИЕ: Убираем узлы без транзакций (sent=0 AND received=0)
            nodes_to_remove = []
            start_wallet = st.session_state.get('selected_wallet')
            for node in G.nodes():
                if node == start_wallet:
                    continue  # Не удаляем стартовый кошелек
                tx_count = G.nodes[node].get("transaction_count", 0)
                total_sent = G.nodes[node].get("total_sent", 0)
                total_received = G.nodes[node].get("total_received", 0)
                if tx_count == 0 and total_sent == 0 and total_received == 0:
                    nodes_to_remove.append(node)
            
            if nodes_to_remove:
                G.remove_nodes_from(nodes_to_remove)
                logger.info(f"Removed {len(nodes_to_remove)} nodes with no transactions in filtered data")
            
            logger.info(f"Final graph: {len(G.nodes())} nodes, {len(G.edges())} edges")
            
            if len(G.nodes()) == 0:
                st.warning("⚠️ Graph has no nodes. Check if data is being fetched correctly.")
                return None
            
            # Get node size metric from sidebar
            node_size_mapping = {
                "Transaction count": "Transaction count",
                "Total volume": "Total volume",
                "Unique connections": "Unique connections",
                "Equal size": "Equal size"
            }
            
            logger.info(f"Creating interactive figure with layout={st.session_state.graph_layout}")
            
            # Get selected asset for tooltips
            selected_asset = st.session_state.asset_filter[0] if st.session_state.asset_filter else "XLM"
            if selected_asset == "All":
                selected_asset = "XLM"  # Default to XLM for "All"
            
            # Create interactive figure
            graph_fig = self.enhanced_graph_builder.create_interactive_figure(
                G,
                layout_type=st.session_state.graph_layout,
                node_size_metric="Transaction count",  # Default for now
                show_labels=True,
                highlight_node=st.session_state.highlight_wallet,
                center_node=st.session_state.center_wallet,
                start_wallet=st.session_state.get('selected_wallet'),  # Pass starting wallet!
                selected_asset=selected_asset  # ← NEW: Pass selected asset for tooltips
            )
            
            logger.info("✅ Graph created successfully")
            return graph_fig
            
        except Exception as e:
            logger.error(f"❌ GRAPH ERROR: {type(e).__name__}: {str(e)}", exc_info=True)
            st.error(f"❌ Error creating graph: {str(e)[:100]}")
            return None
    
    def render_sample_graph(self):
        """Render a sample graph for demonstration."""
        # Create a simple sample graph
        st.info("Sample visualization will be shown here once you fetch network data.")
        
        # Create a minimal example graph
        G = nx.karate_club_graph()
        pos = nx.spring_layout(G)
        
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')
        
        node_x = []
        node_y = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            marker=dict(
                showscale=True,
                colorscale='YlGnBu',
                size=10,
                colorbar=dict(
                    thickness=15,
                    title='Node Connections',
                    xanchor='left'
                )
            ))
        
        fig = go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=0),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                        )
        
        st.plotly_chart(fig, width="stretch")
    
    def render_wallet_analysis(self, data: Dict):
        """Render wallet analysis section."""
        st.markdown("### 🏆 Top Wallets by Activity")
        
        # Use wallet analyzer to get metrics
        df_metrics = self.wallet_analyzer.calculate_wallet_metrics(
            data["wallets"], 
            data["transactions"]
        )
        
        if not df_metrics.empty:
            # Ranking options
            col1, col2, col3 = st.columns(3)
            with col1:
                rank_by = st.selectbox(
                    "Rank by:",
                    options=["activity_score", "total_volume", "total_transactions", "unique_counterparties"],
                    format_func=lambda x: {
                        "activity_score": "Activity Score",
                        "total_volume": "Total Volume",
                        "total_transactions": "Transaction Count",
                        "unique_counterparties": "Unique Connections"
                    }[x]
                )
            
            with col2:
                show_top = st.slider("Show top:", 5, 20, 10)
            
            with col3:
                identify_types = st.checkbox("Identify wallet types", value=True)
            
            # Sort and filter
            df_display = df_metrics.sort_values(rank_by, ascending=False).head(show_top)
            
            # Add wallet types if requested
            if identify_types:
                wallet_types = self.wallet_analyzer.identify_wallet_types(
                    data["wallets"], 
                    data["transactions"]
                )
                df_display["type"] = df_display["wallet_id"].map(wallet_types)
                
                # Add type emoji
                type_emoji = {
                    "exchange": "🏦",
                    "holder": "💎",
                    "bot_trader": "🤖",
                    "distributor": "📤",
                    "collector": "📥",
                    "regular": "👤"
                }
                df_display["type_icon"] = df_display["type"].map(type_emoji)
            
            # Display metrics table
            display_columns = [
                "wallet_short",
                "type_icon" if identify_types else None,
                "activity_score",
                "total_transactions",
                "total_volume",
                "unique_counterparties",
                "balance_xlm"
            ]
            display_columns = [c for c in display_columns if c]
            
            # Rename columns for display
            column_names = {
                "wallet_short": "Wallet",
                "type_icon": "Type",
                "activity_score": "Activity",
                "total_transactions": "Txns",
                "total_volume": "Volume",
                "unique_counterparties": "Connections",
                "balance_xlm": "Balance"
            }
            
            st.dataframe(
                df_display[display_columns].rename(columns=column_names),
                width="stretch",
                hide_index=True
            )
            
            # Show distribution charts
            st.markdown("#### 📊 Distribution Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Volume distribution
                fig_volume = go.Figure(data=[
                    go.Bar(
                        x=df_display["wallet_short"],
                        y=df_display["total_volume"],
                        marker_color='lightblue',
                        text=df_display["total_volume"].round(2),
                        textposition='auto',
                    )
                ])
                fig_volume.update_layout(
                    title="Volume Distribution",
                    xaxis_title="Wallet",
                    yaxis_title="Total Volume (XLM)",
                    height=300,
                    showlegend=False
                )
                st.plotly_chart(fig_volume, width="stretch")
            
            with col2:
                # Transaction count distribution
                fig_tx = go.Figure(data=[
                    go.Bar(
                        x=df_display["wallet_short"],
                        y=df_display["total_transactions"],
                        marker_color='lightgreen',
                        text=df_display["total_transactions"],
                        textposition='auto',
                    )
                ])
                fig_tx.update_layout(
                    title="Transaction Count",
                    xaxis_title="Wallet",
                    yaxis_title="Number of Transactions",
                    height=300,
                    showlegend=False
                )
                st.plotly_chart(fig_tx, width="stretch")
            
            # Wallet details section
            st.markdown("#### 🔍 Detailed Wallet View")
            selected_wallet = st.selectbox(
                "Select wallet for detailed analysis:",
                options=df_metrics["wallet_id"].tolist(),
                format_func=lambda x: f"{x[:8]}...{x[-8:]}"
            )
            
            if selected_wallet:
                self.render_wallet_details(selected_wallet, data, df_metrics)
    
    def render_wallet_details(self, wallet_id: str, data: Dict, df_metrics: pd.DataFrame = None):
        """Render detailed information for a specific wallet."""
        wallet_data = data["wallets"].get(wallet_id, {})
        
        # Get metrics for this wallet
        if df_metrics is not None and not df_metrics.empty:
            wallet_metrics = df_metrics[df_metrics["wallet_id"] == wallet_id].iloc[0] if len(df_metrics[df_metrics["wallet_id"] == wallet_id]) > 0 else None
        else:
            wallet_metrics = None
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("##### 📋 Wallet Information")
            st.text(f"Address: {wallet_id[:12]}...")
            st.text(f"Balance: {wallet_data.get('balance_xlm', 0):.2f} XLM")
            if wallet_metrics is not None:
                st.text(f"Activity Score: {wallet_metrics.get('activity_score', 0):.2f}")
                st.text(f"Overall Rank: #{int(wallet_metrics.get('overall_rank', 0))}")
            
        with col2:
            st.markdown("##### 📊 Transaction Statistics")
            
            # Calculate stats
            sent_txs = [tx for tx in data["transactions"] if tx.get("from") == wallet_id]
            received_txs = [tx for tx in data["transactions"] if tx.get("to") == wallet_id]
            
            st.text(f"Sent: {len(sent_txs)} transactions")
            st.text(f"Received: {len(received_txs)} transactions")
            st.text(f"Total sent: {sum(float(tx.get('amount', 0)) for tx in sent_txs):.2f} XLM")
            st.text(f"Total received: {sum(float(tx.get('amount', 0)) for tx in received_txs):.2f} XLM")
    
    def render_transactions_table(self, data: Dict):
        """Render transactions table."""
        st.markdown("### Recent Transactions")
        
        # Convert transactions to DataFrame
        tx_list = []
        for tx in data["transactions"]:
            # Parse date properly
            created_at = tx.get('created_at', '')
            if isinstance(created_at, datetime):
                date_obj = created_at
                date_str = created_at.strftime("%Y-%m-%d %H:%M")
            elif isinstance(created_at, str):
                try:
                    date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                except:
                    date_obj = None
                    date_str = created_at
            else:
                date_obj = None
                date_str = ""
            
            tx_list.append({
                "From": f"{tx.get('from', '')[:8]}..." if tx.get('from') else "",
                "To": f"{tx.get('to', '')[:8]}..." if tx.get('to') else "",
                "Amount": float(tx.get('amount', 0)),
                "Asset": tx.get('asset_code', 'XLM'),
                "Type": tx.get('type', 'unknown'),
                "Date": date_str,
                "_date_sort": date_obj if date_obj else datetime.min  # For sorting
            })
        
        if tx_list:
            df = pd.DataFrame(tx_list)
            
            # Sort by date descending (most recent first)
            df = df.sort_values('_date_sort', ascending=False)
            
            # Now format Amount as string for display
            df['Amount'] = df['Amount'].apply(lambda x: f"{x:.2f}")
            
            # Remove hidden _date_sort column
            df = df.drop('_date_sort', axis=1)
            
            st.dataframe(df, width="stretch", hide_index=True)
        else:
            st.info("No transactions found")
    
    def render_network_metrics(self, data: Dict):
        """Render network analysis metrics."""
        st.markdown("### Network Metrics")
        
        # Build NetworkX graph for analysis
        G = nx.Graph()
        for wallet_id in data["wallets"]:
            G.add_node(wallet_id)
        
        for tx in data["transactions"]:
            if "from" in tx and "to" in tx:
                if tx["from"] in G.nodes and tx["to"] in G.nodes:
                    G.add_edge(tx["from"], tx["to"])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Basic Metrics")
            st.metric("Nodes", G.number_of_nodes())
            st.metric("Edges", G.number_of_edges())
            st.metric("Density", f"{nx.density(G):.4f}")
        
        with col2:
            st.markdown("#### Centrality")
            if G.number_of_nodes() > 0:
                degree_centrality = nx.degree_centrality(G)
                top_central = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:3]
                
                st.text("Top 3 by Degree Centrality:")
                for wallet, score in top_central:
                    st.text(f"{wallet[:8]}...: {score:.3f}")
        
        with col3:
            st.markdown("#### Components")
            components = list(nx.connected_components(G))
            st.metric("Connected Components", len(components))
            if components:
                st.metric("Largest Component", len(max(components, key=len)))
    
    
    
    def render_path_finder(self, data: Dict):
        """Render Path Finder tool on separate tab."""
        st.markdown("### 🔎 Find Connection Between Wallets")
        
        st.markdown("""
        This tool helps you find potential connections between two wallets 
        by searching for transaction paths through intermediaries.
        
        **Use cases:**
        - Track money laundering attempts  
        - Find hidden connections between wallets
        - Investigate suspicious transactions
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            wallet_from = st.text_input(
                "Wallet A (From):",
                placeholder="GABC...",
                help="Enter the first wallet address (56 characters)",
                key="path_wallet_from"
            )
        with col2:
            wallet_to = st.text_input(
                "Wallet B (To):",
                placeholder="GXYZ...",
                help="Enter the second wallet address (56 characters)",
                key="path_wallet_to"
            )
        
        max_path_length = st.slider(
            "Maximum path length (hops):",
            min_value=1,
            max_value=5,
            value=3,
            help="How many intermediary wallets to search through",
            key="path_max_length"
        )
        
        if st.button("🔎 Find Path", type="primary", key="find_path_btn"):
            if not wallet_from or not wallet_to:
                st.error("Please enter both wallet addresses")
            elif len(wallet_from) != 56 or not wallet_from.startswith("G"):
                st.error("Wallet A address is invalid (must be 56 characters starting with G)")
            elif len(wallet_to) != 56 or not wallet_to.startswith("G"):
                st.error("Wallet B address is invalid (must be 56 characters starting with G)")
            elif wallet_from == wallet_to:
                st.warning("Both wallets are the same!")
            else:
                # Build graph from transactions
                import networkx as nx
                G = nx.DiGraph()
                
                for tx in data["transactions"]:
                    from_w = tx.get("from")
                    to_w = tx.get("to")
                    amount = float(tx.get("amount", 0))
                    
                    if from_w and to_w:
                        if G.has_edge(from_w, to_w):
                            G[from_w][to_w]["weight"] += amount
                            G[from_w][to_w]["count"] += 1
                        else:
                            G.add_edge(from_w, to_w, weight=amount, count=1)
                
                # Check if wallets exist in GRAPH (not in data["wallets"])
                wallet_from_exists = wallet_from in G.nodes()
                wallet_to_exists = wallet_to in G.nodes()
                
                if not wallet_from_exists and not wallet_to_exists:
                    st.error(f"❌ Neither wallet found in current network.")
                    st.info("""
                    **Tip:** These wallets are not in the loaded network data. Try:
                    1. Fetching data for one of these wallets first
                    2. Increasing 'Max wallets' to load more connections
                    3. Adjusting filters to include more transactions
                    """)
                    return
                elif not wallet_from_exists:
                    st.error(f"❌ Wallet A not found in current network.")
                    st.info("Try fetching data for this wallet or increasing 'Max wallets' setting.")
                    return
                elif not wallet_to_exists:
                    st.error(f"❌ Wallet B not found in current network.")
                    st.info("Try fetching data for this wallet or increasing 'Max wallets' setting.")
                    return
                
                # Find path using NetworkX
                try:
                    with st.spinner("🔍 Searching for path..."):
                        # Try to find shortest path
                        if nx.has_path(G, wallet_from, wallet_to):
                            path = nx.shortest_path(G, wallet_from, wallet_to)
                            
                            if len(path) - 1 > max_path_length:
                                st.warning(f"⚠️ Path found but it's too long ({len(path)-1} hops). Increase max path length.")
                                return
                            
                            # Calculate total flow through path
                            total_flow = min(G[path[i]][path[i+1]]["weight"] for i in range(len(path)-1))
                            
                            # Get selected asset for display
                            selected_asset = st.session_state.asset_filter[0] if st.session_state.asset_filter else "XLM"
                            if selected_asset == "All":
                                selected_asset = "XLM"
                            
                            # Display results
                            st.success(f"✅ Path found! {len(path)-1} hop(s)")
                            
                            st.markdown("### 📍 Path Details:")
                            
                            for i, wallet in enumerate(path):
                                wallet_short = f"{wallet[:8]}...{wallet[-4:]}"
                                is_start = (i == 0)
                                is_end = (i == len(path) - 1)
                                
                                if is_start:
                                    st.markdown(f"**🎯 START:** `{wallet_short}`")
                                    st.code(wallet, language=None)
                                elif is_end:
                                    st.markdown(f"**🎯 TARGET:** `{wallet_short}`")
                                    st.code(wallet, language=None)
                                else:
                                    st.markdown(f"**{i}.** Intermediary: `{wallet_short}`")
                                    with st.expander(f"Show full address"):
                                        st.code(wallet, language=None)
                                
                                # Show transaction details
                                if i < len(path) - 1:
                                    next_wallet = path[i + 1]
                                    edge_data = G[wallet][next_wallet]
                                    st.markdown(
                                        f"  ↓ *{edge_data['count']} transaction(s), "
                                        f"total: {edge_data['weight']:,.2f} {selected_asset}*"
                                    )
                                    st.markdown("")
                            
                            st.markdown(f"**💰 Potential max flow through this path:** `{total_flow:,.2f} {selected_asset}`")
                            
                            st.info("""
                            💡 **Interpretation:**
                            - This path shows how funds could flow between wallets
                            - Each step represents actual transactions in the network
                            - The max flow is limited by the smallest transaction in the chain
                            """)
                            
                        else:
                            st.warning("❌ No path found between these wallets in the current network data.")
                            st.info("""
                            **Possible reasons:**
                            - Wallets are not directly or indirectly connected
                            - Path exists but requires more hops (try increasing max length)
                            - Path involves wallets not in current network (try increasing max_wallets)
                            """)
                
                except nx.NetworkXNoPath:
                    st.warning("❌ No path found between these wallets.")
                except Exception as e:
                    st.error(f"❌ Error searching for path: {str(e)}")
                    logger.error(f"Path finding error: {e}", exc_info=True)
    
    def render_raw_data(self, data: Dict):
        """Render raw data for debugging."""
        st.markdown("### Raw Data")
        
        with st.expander("View raw network data"):
            st.json({
                "stats": data["stats"],
                "wallet_count": len(data["wallets"]),
                "transaction_count": len(data["transactions"])
            })
    


# Run the app
if __name__ == "__main__":
    app = StellarVizApp()
    app.run()
