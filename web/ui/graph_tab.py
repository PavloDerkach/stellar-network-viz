"""Graph visualization tab module."""
import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, Any, Optional
import logging
import sys
from pathlib import Path

# FIX PATHS
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.graph_builder import UnifiedGraphBuilder
from src.analysis.wallet_analyzer import WalletAnalyzer

logger = logging.getLogger(__name__)


class GraphTab:
    """Handle graph visualization tab."""
    
    def __init__(self, graph_builder: Optional[UnifiedGraphBuilder] = None):
        """Initialize graph tab."""
        self.graph_builder = graph_builder or UnifiedGraphBuilder()
        self.wallet_analyzer = WalletAnalyzer()
    
    def render(self, data: Dict[str, Any]):
        """Render the network graph tab."""
        if not data or not data.get("wallets") or not data.get("transactions"):
            st.error("⚠️ No data to display")
            return
        
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            wallet_options = ["None"] + list(data["wallets"].keys())
            highlight_idx = 0
            if st.session_state.highlight_wallet in wallet_options:
                highlight_idx = wallet_options.index(st.session_state.highlight_wallet)
            
            selected_highlight = st.selectbox(
                "🔍 Highlight wallet:",
                options=wallet_options,
                index=highlight_idx,
                format_func=lambda x: "None (show all)" if x == "None" else f"{x[:8]}...{x[-8:]}"
            )
            
            st.session_state.highlight_wallet = None if selected_highlight == "None" else selected_highlight
        
        with col2:
            center_options = ["None"] + list(data["wallets"].keys())
            center_idx = 0
            if st.session_state.center_wallet in center_options:
                center_idx = center_options.index(st.session_state.center_wallet)
            
            selected_center = st.selectbox(
                "🎯 Center on wallet:",
                options=center_options,
                index=center_idx,
                format_func=lambda x: "Default" if x == "None" else f"{x[:8]}...{x[-8:]}"
            )
            
            st.session_state.center_wallet = None if selected_center == "None" else selected_center
        
        with col3:
            if st.button("🔄 Reset View"):
                st.session_state.highlight_wallet = None
                st.session_state.center_wallet = None
                st.rerun()
        
        with col4:
            with st.popover("ℹ️ Help"):
                st.markdown("""
                **Node colors:**
                - 🔴 Red: Start wallet
                - 🟢 Teal: Connected
                - 🔵 Blue: Others
                """)
        
        with st.spinner(f"🔄 Building graph ({len(data['wallets'])} nodes)..."):
            graph_html = self.create_graph(data)
        
        if graph_html:
            self.display_graph(graph_html, data)
            self.render_wallet_info(data)
        else:
            st.error("❌ Failed to create graph")
    
    def create_graph(self, data: Dict[str, Any]) -> Optional[str]:
        """Create network graph visualization."""
        try:
            min_tx_count = st.session_state.get("min_tx_count", 0)
            
            # Debug: проверяем start_wallet
            start_wallet = data.get("stats", {}).get("start_wallet")
            logger.info(f"🔍 DEBUG: data.keys() = {list(data.keys())}")
            logger.info(f"🔍 DEBUG: data['stats'] = {data.get('stats', {})}")
            logger.info(f"🔍 DEBUG: start_wallet from data = {start_wallet}")
            
            graph_html = self.graph_builder.create_filtered_graph(
                data=data,
                min_tx_count=min_tx_count,
                highlight_node=st.session_state.get("highlight_wallet"),
                center_node=st.session_state.get("center_wallet"),
                start_wallet=start_wallet,  # Используем переменную
                selected_asset=st.session_state.get("asset_filter", ["XLM"])[0],
                transactions=data.get("transactions", []),
                show_labels=False
            )
            
            logger.info("✅ Graph created successfully")
            return graph_html
            
        except Exception as e:
            logger.error(f"Graph creation error: {e}")
            return None
    
    def display_graph(self, graph_html: str, data: Dict[str, Any]):
        """Display the graph with metrics."""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("👥 Wallets", len(data.get("wallets", {})))
        
        with col2:
            st.metric("💸 Transactions", len(data.get("transactions", [])))
        
        with col3:
            st.metric("📊 Data Status", "✅ Complete")
        
        with col4:
            st.metric("💾 Cached", "No")
        
        if len(data.get("wallets", {})) > 100:
            st.info(f"📊 Rendering large graph ({len(data['wallets'])} nodes)...")
        
        try:
            components.html(graph_html, height=720, scrolling=False)
        except Exception as e:
            logger.error(f"Error rendering graph: {e}")
            st.error("⚠️ Graph too large. Apply stricter filters.")
    
    def render_wallet_info(self, data: Dict[str, Any]):
        """Render wallet selection and info."""
        wallet_options = ["None"] + sorted(list(data["wallets"].keys()))
        clicked_idx = st.selectbox(
            "🎯 Select wallet for details:",
            options=range(len(wallet_options)),
            format_func=lambda x: f"{wallet_options[x][:12]}..." if x > 0 else "None"
        )
        
        if clicked_idx > 0:
            selected = wallet_options[clicked_idx]
            st.session_state.clicked_node = selected
            
            wallet_data = data["wallets"].get(selected, {})
            if wallet_data:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Balance", f"{wallet_data.get('balance_xlm', 0):,.2f} XLM")
                with col2:
                    tx_count = len([
                        tx for tx in data["transactions"]
                        if tx.get("from") == selected or tx.get("to") == selected
                    ])
                    st.metric("Transactions", tx_count)
                with col3:
                    st.metric("Created", wallet_data.get("created_at", "Unknown")[:10])
