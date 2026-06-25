import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from agents.sentiment_fusion.fetcher import compute_sentiment_label, compute_social_score


def test_high_votes_positive_price_is_bullish():
    assert compute_sentiment_label(75.0, 5.0) == "bullish"


def test_low_votes_crashing_price_is_bearish():
    assert compute_sentiment_label(30.0, -10.0) == "bearish"


def test_mixed_signals_is_neutral():
    assert compute_sentiment_label(50.0, 1.0) == "neutral"


def test_social_score_bounded_0_to_100():
    assert 0 <= compute_social_score(100.0, 10.0, 1) <= 100
    assert 0 <= compute_social_score(0.0, -20.0, None) <= 100


def test_top_100_rank_adds_bonus():
    without = compute_social_score(60.0, 0.0, None)
    with_rank = compute_social_score(60.0, 0.0, 50)
    assert with_rank > without
