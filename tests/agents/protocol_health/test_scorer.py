import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from agents.protocol_health.fetcher import compute_health_score


def test_high_tvl_audited_scores_high():
    score = compute_health_score(tvl_usd=500_000_000, tvl_24h_change=2.0, audited=True)
    assert score >= 80


def test_low_tvl_crashing_unaudited_scores_low():
    score = compute_health_score(tvl_usd=50_000, tvl_24h_change=-25.0, audited=False)
    assert score <= 20


def test_score_always_bounded_0_to_100():
    assert 0 <= compute_health_score(0, -100.0, False) <= 100
    assert 0 <= compute_health_score(1_000_000_000, 100.0, True) <= 100


def test_audit_bonus_makes_difference():
    without = compute_health_score(tvl_usd=10_000_000, tvl_24h_change=0.0, audited=False)
    with_audit = compute_health_score(tvl_usd=10_000_000, tvl_24h_change=0.0, audited=True)
    assert with_audit > without
