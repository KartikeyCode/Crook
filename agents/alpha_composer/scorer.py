from shared.schemas import (
    WhaleTrackerResponse,
    ProtocolHealthResponse,
    TokenDDResponse,
    SentimentResponse,
    AlphaResponse,
)
from datetime import datetime, timezone


WEIGHTS = {
    "dd": 0.35,
    "whale": 0.25,
    "health": 0.20,
    "sentiment": 0.20,
}

SUB_AGENT_COST_USDC = 0.50  # 4 calls × $0.50 each


def compute_alpha_score(
    whale: WhaleTrackerResponse,
    health: ProtocolHealthResponse,
    dd: TokenDDResponse,
    sentiment: SentimentResponse,
) -> int:
    raw = (
        dd.dd_score * WEIGHTS["dd"]
        + whale.movement_score * WEIGHTS["whale"]
        + health.health_score * WEIGHTS["health"]
        + sentiment.social_score * WEIGHTS["sentiment"]
    )
    return max(0, min(100, round(raw)))


def compute_recommendation(alpha_score: int, dd: TokenDDResponse) -> str:
    if dd.is_honeypot or dd.risk_level == "critical":
        return "avoid"
    if alpha_score >= 70:
        return "strong_buy"
    if alpha_score >= 55:
        return "buy"
    if alpha_score >= 40:
        return "hold"
    return "sell"


def compute_confidence(
    whale: WhaleTrackerResponse,
    health: ProtocolHealthResponse,
    dd: TokenDDResponse,
    sentiment: SentimentResponse,
) -> int:
    degraded_count = sum(
        1 for r in [whale.data_quality, health.data_quality, dd.data_quality, sentiment.data_quality]
        if r == "degraded"
    )
    base = 90
    return max(10, base - degraded_count * 20)


def build_summary(
    alpha_score: int,
    recommendation: str,
    whale: WhaleTrackerResponse,
    health: ProtocolHealthResponse,
    dd: TokenDDResponse,
    sentiment: SentimentResponse,
) -> str:
    parts = [
        f"Alpha score {alpha_score}/100 → {recommendation.upper()}.",
        f"Whale flow: {whale.net_flow} ({whale.whale_count} txs).",
        f"Protocol TVL: ${health.tvl_usd:,.0f} ({health.audit_status}).",
        f"DD: {dd.risk_level} risk, score {dd.dd_score}.",
        f"Sentiment: {sentiment.sentiment} ({sentiment.price_change_24h_pct:+.1f}% 24h).",
    ]
    if dd.risk_flags:
        parts.append(f"Flags: {', '.join(dd.risk_flags)}.")
    return " ".join(parts)


def compose_alpha(
    whale: WhaleTrackerResponse,
    health: ProtocolHealthResponse,
    dd: TokenDDResponse,
    sentiment: SentimentResponse,
    partial: bool = False,
) -> AlphaResponse:
    alpha_score = compute_alpha_score(whale, health, dd, sentiment)
    recommendation = compute_recommendation(alpha_score, dd)
    confidence = compute_confidence(whale, health, dd, sentiment)

    return AlphaResponse(
        alpha_score=alpha_score,
        recommendation=recommendation,
        confidence_pct=confidence,
        whale_activity=whale.model_dump(),
        protocol_health=health.model_dump(),
        token_dd=dd.model_dump(),
        sentiment=sentiment.model_dump(),
        summary=build_summary(alpha_score, recommendation, whale, health, dd, sentiment),
        generated_at=datetime.now(timezone.utc).isoformat(),
        sub_agent_costs_usdc=SUB_AGENT_COST_USDC,
        partial_report=partial,
    )
