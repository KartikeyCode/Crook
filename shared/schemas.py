from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Chain(str, Enum):
    BASE = "base"
    ETHEREUM = "ethereum"


# --- Whale Tracker ---
class WhaleTrackerRequest(BaseModel):
    token_address: str
    chain: Chain
    lookback_hours: int = 24


class LargeMovement(BaseModel):
    wallet: str
    amount_usd: float
    direction: str
    tx_hash: str


class WhaleTrackerResponse(BaseModel):
    large_movements: list[LargeMovement]
    net_flow: str
    movement_score: int
    whale_count: int
    data_quality: str


# --- Protocol Health ---
class ProtocolHealthRequest(BaseModel):
    token_address: str
    chain: Chain


class ProtocolHealthResponse(BaseModel):
    protocol_name: str
    tvl_usd: float
    tvl_24h_change_pct: float
    tvl_7d_change_pct: float
    audit_status: str
    auditor: str
    chain_count: int
    health_score: int
    data_quality: str


# --- Token DD ---
class TokenDDRequest(BaseModel):
    token_address: str
    chain: Chain


class TokenDDResponse(BaseModel):
    is_honeypot: bool
    can_sell: bool
    ownership_renounced: bool
    contract_verified: bool
    liquidity_locked: bool
    buy_tax_pct: float
    sell_tax_pct: float
    risk_flags: list[str]
    risk_level: str
    dd_score: int
    data_quality: str


# --- Sentiment Fusion ---
class SentimentRequest(BaseModel):
    token_address: str
    token_symbol: str = ""
    chain: Chain


class SentimentResponse(BaseModel):
    sentiment: str
    social_score: int
    sentiment_votes_up_pct: float
    sentiment_votes_down_pct: float
    price_change_24h_pct: float
    volume_spike_24h: bool
    market_cap_rank: Optional[int]
    data_quality: str


# --- Alpha Composer ---
class AlphaRequest(BaseModel):
    token_address: str
    chain: Chain
    token_symbol: str = ""


class AlphaResponse(BaseModel):
    alpha_score: int
    recommendation: str
    confidence_pct: int
    whale_activity: dict
    protocol_health: dict
    token_dd: dict
    sentiment: dict
    summary: str
    generated_at: str
    sub_agent_costs_usdc: float
    partial_report: bool
