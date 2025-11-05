"""
Stellar Network Visualization - FIXED VERSION
"""
import streamlit as st
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
from pathlib import Path

# FIX PATHS - ADD PARENT DIR TO PATH
sys.path.append(str(Path(__file__).parent.parent))

# Now imports will work
from ui.filters import FilterPanel
from ui.graph_tab import GraphTab  
from data.fetcher import DataFetcher
from core.graph_builder import UnifiedGraphBuilder
from src.api.stellar_client import StellarClient
from src.analysis.wallet_analyzer import WalletAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Stellar Network Visualization",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed"
)


class StellarVizApp:
    """Main application class."""
    
    def __init__(self):
        """Initialize app components."""
        self.client = StellarClient()
        self.fetcher = DataFetcher(self.client)
        self.graph_builder = UnifiedGraphBuilder(backend="pyvis")
        self.wallet_analyzer = WalletAnalyzer()
        
        self.filter_panel = FilterPanel()
        self.graph_tab = GraphTab(self.graph_builder)
        
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables."""
        defaults = {
            "network_data": None,
            "selected_wallet": None,
            "graph_layout": "force",
            "highlight_wallet": None,
            "center_wallet": None,
            "asset_filter": ["USDC"],
            "tx_type_filter": ["All"],
            "date_from": (datetime.now() - timedelta(days=365)).date(),
            "date_to": datetime.now().date(),
            "direction_filter": ["All"],
            "min_amount": None,
            "max_amount": None,
            "min_tx_count": 0,
            "clicked_node": None
        }
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    def run(self):
        """Run the application."""
        self.render_header()
        config = self.filter_panel.render_top_controls()
        
        if config["clear_clicked"]:
            self.clear_cache()
        
        if config["fetch_clicked"]:
            data = self.fetcher.fetch_network_data(
                wallet_address=config["wallet_address"],
                max_wallets=config["max_wallets"],
                strategy=config["strategy"],
                asset_filter=st.session_state.asset_filter if st.session_state.asset_filter and "All" not in st.session_state.asset_filter else None,
                date_from=st.session_state.date_from if hasattr(st.session_state, 'date_from') else None,
                date_to=st.session_state.date_to if hasattr(st.session_state, 'date_to') else None,
                max_pages=config["max_pages"]
            )
            if data:
                st.session_state.network_data = data
                st.success(f"✅ Loaded {len(data['wallets'])} wallets, {len(data['transactions'])} transactions")
                st.rerun()
        
        if st.session_state.network_data:
            self.render_main_content()
        else:
            self.render_welcome()
    
    def render_header(self):
        """Render app header."""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🌟 Stellar Network Visualization")
            st.caption("Explore wallet connections in the Stellar blockchain")
    
    def render_welcome(self):
        """Render welcome screen."""
        st.info("👆 Enter a wallet address and click **Fetch** to start exploring")
        
        with st.expander("🚀 Quick Start"):
            st.markdown("""
            **Example wallets:**
            - `GAYFS6KPNCE5II2YGJMONCBDJ2UF5WQBUQKNBDAHXKOURI466QPAQ3JZ`
            - `GAAVMJ53OUWEPLAYHKATE2XWQAU66KGL6LTH7IR3S4CR7HL2RABIS2U5`
            """)
    
    def render_main_content(self):
        """Render main content area."""
        data = st.session_state.network_data
        
        self.show_active_filters()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Wallets", data["stats"]["total_wallets"])
        with col2:
            st.metric("Total Transactions", data["stats"]["total_transactions"])
        with col3:
            total_volume = sum(float(tx.get("amount", 0)) for tx in data["transactions"])
            st.metric("Total Volume", f"{total_volume:,.2f}")
        
        filter_settings = self.filter_panel.render_graph_filters()
        
        tab1, tab2 = st.tabs(["📊 Network Graph", "💹 Analysis"])
        
        with tab1:
            self.graph_tab.render(data)
        
        with tab2:
            self.render_analysis_tab(data)
    
    def show_active_filters(self):
        """Show currently active filters."""
        filters = []
        
        if st.session_state.asset_filter and "All" not in st.session_state.asset_filter:
            filters.append(f"**Asset**: {', '.join(st.session_state.asset_filter)}")
        
        if st.session_state.min_tx_count > 0:
            filters.append(f"**Min TXs**: {st.session_state.min_tx_count}")
        
        if filters:
            st.info(f"🎯 Active Filters: {' | '.join(filters)}")
    
    def render_analysis_tab(self, data: Dict):
        """Render analysis tab."""
        st.markdown("### 🏆 Top Wallets by Activity")
        
        df_metrics = self.wallet_analyzer.calculate_wallet_metrics(
            data["wallets"],
            data["transactions"]
        )
        
        if not df_metrics.empty:
            col1, col2 = st.columns(2)
            with col1:
                rank_by = st.selectbox(
                    "Rank by:",
                    options=["activity_score", "total_volume", "total_transactions"]
                )
            with col2:
                show_top = st.slider("Show top:", 5, 20, 10)
            
            df_display = df_metrics.sort_values(rank_by, ascending=False).head(show_top)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    def clear_cache(self):
        """Clear all caches."""
        st.cache_data.clear()
        st.session_state.network_data = None
        st.success("✅ Cache cleared!")
        st.rerun()


if __name__ == "__main__":
    app = StellarVizApp()
    app.run()
