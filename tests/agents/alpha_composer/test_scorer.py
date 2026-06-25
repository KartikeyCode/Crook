import pytest
from shared.schemas import (
    WhaleTrackerResponse,
    ProtocolHealthResponse,
    TokenDDResponse,
    SentimentResponse,
)
from agents.alpha_composer.scorer import (
    compute_alpha_score,
    compute_recommendation,
    compute_confidence,
    compose_alpha,
)


def _make_whale(score=70, net_flow="inflow", quality="full"):
    return WhaleTrackerResponse(
        large_movements=[], net_flow=net_flow,
        movement_score=score, whale_count=5, data_quality=quality,
    )


def _make_health(score=75, quality="full"):
    return ProtocolHealthResponse(
        protocol_name="Test", tvl_usd=50_000_000,
        tvl_24h_change_pct=2.0, tvl_7d_change_pct=5.0,
        audit_status="audited", auditor="CertiK",
        chain_count=3, health_score=score, data_quality=quality,
    )


def _make_dd(score=80, honeypot=False, risk="low", quality="full"):
    return TokenDDResponse(
        is_honeypot=honeypot, can_sell=True, ownership_renounced=True,
        contract_verified=True, liquidity_locked=True,
        buy_tax_pct=1.0, sell_tax_pct=1.0,
        risk_flags=[], risk_level=risk,
        dd_score=score, data_quality=quality,
    )


def _make_sentiment(score=65, quality="full"):
    return SentimentResponse(
        sentiment="bullish", social_score=score,
        sentiment_votes_up_pct=65.0, sentiment_votes_down_pct=35.0,
        price_change_24h_pct=3.0, volume_spike_24h=False,
        market_cap_rank=50, data_quality=quality,
    )


def test_alpha_score_weighted():
    whale = _make_whale(score=80)
    health = _make_health(score=60)
    dd = _make_dd(score=90)
    sentiment = _make_sentiment(score=70)
    score = compute_alpha_score(whale, health, dd, sentiment)
    expected = round(90 * 0.35 + 80 * 0.25 + 60 * 0.20 + 70 * 0.20)
    assert score == expected


def test_alpha_score_clamped_to_100():
    whale = _make_whale(score=100)
    health = _make_health(score=100)
    dd = _make_dd(score=100)
    sentiment = _make_sentiment(score=100)
    assert compute_alpha_score(whale, health, dd, sentiment) == 100


def test_alpha_score_clamped_to_zero():
    whale = _make_whale(score=0)
    health = _make_health(score=0)
    dd = _make_dd(score=0)
    sentiment = _make_sentiment(score=0)
    assert compute_alpha_score(whale, health, dd, sentiment) == 0


def test_recommendation_honeypot_always_avoid():
    dd = _make_dd(honeypot=True, risk="critical")
    assert compute_recommendation(90, dd) == "avoid"


def test_recommendation_critical_risk_avoid():
    dd = _make_dd(risk="critical")
    assert compute_recommendation(80, dd) == "avoid"


def test_recommendation_strong_buy():
    dd = _make_dd(risk="low")
    assert compute_recommendation(75, dd) == "strong_buy"


def test_recommendation_buy():
    dd = _make_dd(risk="low")
    assert compute_recommendation(60, dd) == "buy"


def test_recommendation_hold():
    dd = _make_dd(risk="low")
    assert compute_recommendation(45, dd) == "hold"


def test_recommendation_sell():
    dd = _make_dd(risk="low")
    assert compute_recommendation(30, dd) == "sell"


def test_confidence_all_full():
    whale = _make_whale(quality="full")
    health = _make_health(quality="full")
    dd = _make_dd(quality="full")
    sentiment = _make_sentiment(quality="full")
    assert compute_confidence(whale, health, dd, sentiment) == 90


def test_confidence_degraded_reduces():
    whale = _make_whale(quality="degraded")
    health = _make_health(quality="degraded")
    dd = _make_dd(quality="full")
    sentiment = _make_sentiment(quality="full")
    assert compute_confidence(whale, health, dd, sentiment) == 50


def test_compose_alpha_returns_valid_response():
    whale = _make_whale()
    health = _make_health()
    dd = _make_dd()
    sentiment = _make_sentiment()
    result = compose_alpha(whale, health, dd, sentiment)
    assert 0 <= result.alpha_score <= 100
    assert result.recommendation in {"strong_buy", "buy", "hold", "sell", "avoid"}
    assert 0 <= result.confidence_pct <= 100
    assert result.partial_report is False
    assert result.sub_agent_costs_usdc == 0.50


def test_compose_alpha_partial_flag():
    whale = _make_whale(quality="degraded")
    health = _make_health()
    dd = _make_dd()
    sentiment = _make_sentiment()
    result = compose_alpha(whale, health, dd, sentiment, partial=True)
    assert result.partial_report is True
