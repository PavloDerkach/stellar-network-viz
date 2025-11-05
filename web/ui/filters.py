"""UI components for filters and controls."""
import streamlit as st
from datetime import date, timedelta
from typing import Dict, Any


class FilterPanel:
    """Handle all filter UI components."""
    
    @staticmethod
    def render_top_controls() -> Dict[str, Any]:
        """Render top control panel and return config."""
        st.markdown("### ⚙️ Configuration & Filters")
        
        # Wallet address
        wallet_address = st.text_input(
            "🔍 Stellar Wallet Address:",
            value="GAAVMJ53OUWEPLAYHKATE2XWQAU66KGL6LTH7IR3S4CR7HL2RABIS2U5",
            placeholder="Enter wallet address (56 characters, starts with G)",
            help="Enter a valid Stellar wallet address"
        )
        
        # Filters row
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            asset_filter = st.selectbox(
                "Asset:",
                options=["All", "XLM", "USDC", "USDT", "BTC", "ETH"],
                index=2,  # USDC default
                help="Filter transactions by asset type"
            )
            st.session_state.asset_filter = [asset_filter]
        
        with col2:
            default_date_from = date(2021, 11, 4)
            date_from = st.date_input(
                "Date From:",
                value=default_date_from,
                help="Start date for transaction filtering"
            )
            st.session_state.date_from = date_from
        
        with col3:
            date_to = st.date_input(
                "Date To:",
                value=date.today(),
                help="End date for transaction filtering"
            )
            st.session_state.date_to = date_to
        
        # Config row
        col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 1, 1])
        
        with col1:
            max_wallets = st.number_input(
                "Max Wallets",
                min_value=10,
                max_value=200,
                value=200,
                step=10,
                help="Maximum number of wallets to fetch"
            )
        
        with col2:
            strategy = st.selectbox(
                "Strategy:",
                options=["most_active", "breadth_first"],
                index=1,  # Breadth First default
                format_func=lambda x: "🎯 Most Active" if x == "most_active" else "🌐 Breadth First",
                help="Wallet selection strategy"
            )
        
        with col3:
            max_pages_options = {
                "⚡ Fast (~2K)": 10,
                "⚙️ Normal (~10K)": 50,
                "📈 Extended (~20K)": 100,
                "🔥 Full (~40K)": 200,
            }
            max_pages_choice = st.selectbox(
                "Data Limit:",
                options=list(max_pages_options.keys()),
                index=2,
                help="Amount of transaction data to fetch"
            )
            max_pages = max_pages_options[max_pages_choice]
            st.session_state.max_pages = max_pages
            
            # DEBUG LOG: Проверяем что max_pages установлен правильно
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🔍 [filters.py] max_pages установлен: {max_pages} (выбор: '{max_pages_choice}')")
        
        fetch_clicked = False
        clear_clicked = False
        
        with col4:
            if st.button("🚀 Fetch", type="primary", use_container_width=True):
                if wallet_address and len(wallet_address) == 56 and wallet_address.startswith("G"):
                    fetch_clicked = True
                else:
                    st.error("❌ Invalid wallet address!")
        
        with col5:
            if st.button("🗑️ Clear Cache", use_container_width=True):
                clear_clicked = True
        
        st.divider()
        
        return {
            "wallet_address": wallet_address,
            "max_wallets": max_wallets,
            "strategy": strategy,
            "max_pages": max_pages,
            "fetch_clicked": fetch_clicked,
            "clear_clicked": clear_clicked
        }
    
    @staticmethod
    def render_graph_filters() -> Dict[str, Any]:
        """Render graph visualization filters."""
        st.markdown("### 🎨 Graph Filters & Visualization Settings")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            tx_type_filter = st.multiselect(
                "TX Types:",
                options=["payment", "create_account", "path_payment", "All"],
                default=["All"],
                help="Filter by transaction type"
            )
            st.session_state.tx_type_filter = tx_type_filter
        
        with col2:
            direction_filter = st.multiselect(
                "Direction:",
                options=["Sent", "Received", "All"],
                default=["All"],
                help="Filter by transaction direction"
            )
            st.session_state.direction_filter = direction_filter
        
        with col3:
            min_tx_count = st.number_input(
                "Min TXs:",
                min_value=0,
                max_value=100,
                value=0,
                step=1,
                help="Minimum transactions between wallets"
            )
            st.session_state.min_tx_count = min_tx_count
        
        with col4:
            show_labels = st.checkbox(
                "Labels",
                value=True,
                help="Show/hide wallet labels"
            )
        
        with col5:
            node_size_metric = st.selectbox(
                "Node Size:",
                options=["Transaction count", "Total volume", "Equal size"],
                index=0
            )
        
        # Advanced filters
        with st.expander("🔧 Advanced Filters"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                use_amount_filter = st.checkbox("Amount Filter")
                if use_amount_filter:
                    min_amount = st.number_input("Min Amount:", min_value=0.0, value=0.0)
                    max_amount = st.number_input("Max Amount:", min_value=0.0, value=1000000.0)
                    st.session_state.min_amount = min_amount
                    st.session_state.max_amount = max_amount if max_amount > 0 else None
                else:
                    st.session_state.min_amount = None
                    st.session_state.max_amount = None
        
        return {
            "min_tx_count": min_tx_count,
            "show_labels": show_labels,
            "node_size_metric": node_size_metric
        }
