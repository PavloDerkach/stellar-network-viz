"""
Database models for Stellar network visualization.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, DateTime, Numeric, 
    Boolean, ForeignKey, Index, Text, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

Base = declarative_base()


class Wallet(Base):
    """Model for Stellar wallet/account."""
    
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(56), unique=True, nullable=False, index=True)
    
    # Wallet metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)
    
    # Statistics
    total_transactions = Column(Integer, default=0)
    total_sent = Column(Numeric(20, 7), default=0)
    total_received = Column(Numeric(20, 7), default=0)
    unique_counterparties = Column(Integer, default=0)
    
    # Account info from Stellar
    sequence = Column(String(30))
    balance_xlm = Column(Numeric(20, 7))
    num_subentries = Column(Integer)
    flags = Column(Integer)
    thresholds = Column(JSON)
    
    # Analysis metadata
    is_exchange = Column(Boolean, default=False)
    is_anchor = Column(Boolean, default=False)
    trust_score = Column(Numeric(5, 2))
    cluster_id = Column(Integer)
    
    # Relationships
    sent_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.source_wallet_id",
        back_populates="source_wallet"
    )
    received_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.destination_wallet_id",
        back_populates="destination_wallet"
    )
    
    def __repr__(self):
        return f"<Wallet(account_id='{self.account_id[:8]}...', transactions={self.total_transactions})>"


class Transaction(Base):
    """Model for Stellar transactions."""
    
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    # Transaction details
    source_wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    destination_wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    
    operation_type = Column(String(50), nullable=False)  # payment, create_account, etc.
    asset_code = Column(String(12), default="XLM")
    asset_issuer = Column(String(56))
    amount = Column(Numeric(20, 7), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False)
    ledger_close_time = Column(DateTime)
    
    # Transaction metadata
    fee = Column(Integer)
    memo_type = Column(String(20))
    memo_value = Column(Text)
    successful = Column(Boolean, default=True)
    
    # Ledger info
    ledger_sequence = Column(Integer, index=True)
    paging_token = Column(String(30))
    
    # Relationships
    source_wallet = relationship(
        "Wallet",
        foreign_keys=[source_wallet_id],
        back_populates="sent_transactions"
    )
    destination_wallet = relationship(
        "Wallet",
        foreign_keys=[destination_wallet_id],
        back_populates="received_transactions"
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_transaction_time", "created_at"),
        Index("idx_transaction_asset", "asset_code"),
        Index("idx_transaction_wallets", "source_wallet_id", "destination_wallet_id"),
    )
    
    def __repr__(self):
        return f"<Transaction(hash='{self.transaction_hash[:8]}...', amount={self.amount} {self.asset_code})>"


class Asset(Base):
    """Model for Stellar assets."""
    
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_code = Column(String(12), nullable=False)
    asset_issuer = Column(String(56))
    asset_type = Column(String(20))  # native, credit_alphanum4, credit_alphanum12
    
    # Asset statistics
    total_amount = Column(Numeric(30, 7))
    num_accounts = Column(Integer)
    num_transactions = Column(Integer)
    
    # Metadata
    is_verified = Column(Boolean, default=False)
    home_domain = Column(String(255))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint for asset identification
    __table_args__ = (
        Index("idx_unique_asset", "asset_code", "asset_issuer", unique=True),
    )
    
    def __repr__(self):
        return f"<Asset(code='{self.asset_code}', issuer='{self.asset_issuer[:8] if self.asset_issuer else 'native'}...')>"


class NetworkSnapshot(Base):
    """Model for storing network analysis snapshots."""
    
    __tablename__ = "network_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(DateTime, nullable=False, unique=True)
    
    # Network metrics
    total_wallets = Column(Integer)
    total_transactions = Column(Integer)
    total_volume = Column(Numeric(30, 7))
    
    # Graph metrics
    average_degree = Column(Numeric(10, 4))
    clustering_coefficient = Column(Numeric(10, 6))
    network_density = Column(Numeric(10, 8))
    num_components = Column(Integer)
    largest_component_size = Column(Integer)
    
    # Additional analysis
    top_wallets = Column(JSON)  # List of top wallet IDs by various metrics
    top_pairs = Column(JSON)     # Most active wallet pairs
    community_structure = Column(JSON)  # Community detection results
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<NetworkSnapshot(date='{self.snapshot_date}', wallets={self.total_wallets})>"


class CacheEntry(Base):
    """Model for API response caching."""
    
    __tablename__ = "cache_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    response_data = Column(JSON, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    hit_count = Column(Integer, default=0)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<CacheEntry(key='{self.cache_key[:20]}...', expired={self.is_expired()})>"
