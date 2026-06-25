import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from agents.token_dd.fetcher import compute_risk_flags, compute_dd_score


def test_honeypot_is_critical():
    flags, level = compute_risk_flags(True, 2.0, 2.0, True)
    assert "honeypot" in flags
    assert level == "critical"


def test_high_sell_tax_flagged():
    flags, level = compute_risk_flags(False, 2.0, 15.0, True)
    assert "high_sell_tax" in flags
    assert level in ("high", "medium")


def test_clean_token_is_low_risk():
    flags, level = compute_risk_flags(False, 2.0, 2.0, True)
    assert level == "low"


def test_honeypot_scores_zero():
    assert compute_dd_score(True, 0, 0, True, True, True) == 0


def test_perfect_token_scores_above_80():
    assert compute_dd_score(False, 2.0, 2.0, True, True, True) >= 80


def test_dd_score_bounded_0_to_100():
    assert 0 <= compute_dd_score(False, 0, 0, True, True, True) <= 100
    assert 0 <= compute_dd_score(False, 50, 99, False, False, False) <= 100
