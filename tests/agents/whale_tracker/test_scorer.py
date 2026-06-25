import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from agents.whale_tracker.fetcher import compute_movement_score, classify_movement


def test_all_buys_scores_high():
    assert compute_movement_score(buy_count=10, sell_count=0, whale_count=10) >= 80


def test_all_sells_scores_low():
    assert compute_movement_score(buy_count=0, sell_count=10, whale_count=10) <= 20


def test_no_whales_returns_neutral_50():
    assert compute_movement_score(0, 0, 0) == 50


def test_score_bounded_0_to_100():
    assert 0 <= compute_movement_score(1000, 0, 1000) <= 100
    assert 0 <= compute_movement_score(0, 1000, 1000) <= 100


def test_known_dex_classified_as_sell():
    tx = {"to": "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24"}
    assert classify_movement(tx) == "sell"


def test_unknown_address_classified_as_buy():
    tx = {"to": "0x1234567890abcdef1234567890abcdef12345678"}
    assert classify_movement(tx) == "buy"
