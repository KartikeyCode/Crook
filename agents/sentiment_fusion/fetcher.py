from typing import Optional
from shared.data_sources.coingecko import resolve_coin_id, get_coin_data
from shared.schemas import SentimentRequest, SentimentResponse

_DEGRADED = SentimentResponse(
    sentiment="neutral",
    social_score=50,
    sentiment_votes_up_pct=50.0,
    sentiment_votes_down_pct=50.0,
    price_change_24h_pct=0.0,
    volume_spike_24h=False,
    market_cap_rank=None,
    data_quality="degraded",
)


def compute_sentiment_label(votes_up_pct: float, price_change_24h: float) -> str:
    if votes_up_pct >= 60 and price_change_24h >= 0:
        return "bullish"
    if votes_up_pct <= 40 or price_change_24h <= -5:
        return "bearish"
    return "neutral"


def compute_social_score(votes_up_pct: float, price_change_24h: float, rank: Optional[int]) -> int:
    base = int(votes_up_pct)
    momentum = min(10, max(-10, int(price_change_24h)))
    rank_bonus = 5 if rank and rank <= 100 else 0
    return max(0, min(100, base + momentum + rank_bonus))


async def fetch_sentiment(req: SentimentRequest) -> SentimentResponse:
    try:
        coin_id = await resolve_coin_id(req.token_address, req.chain.value, req.token_symbol)
        if not coin_id:
            return _DEGRADED

        data = await get_coin_data(coin_id)
        if not data:
            return _DEGRADED

        votes_up = float(data.get("sentiment_votes_up_percentage") or 50)
        votes_down = float(data.get("sentiment_votes_down_percentage") or 50)
        market = data.get("market_data", {})
        price_change = float(market.get("price_change_percentage_24h") or 0)
        rank = data.get("market_cap_rank")

        return SentimentResponse(
            sentiment=compute_sentiment_label(votes_up, price_change),
            social_score=compute_social_score(votes_up, price_change, rank),
            sentiment_votes_up_pct=round(votes_up, 1),
            sentiment_votes_down_pct=round(votes_down, 1),
            price_change_24h_pct=round(price_change, 2),
            volume_spike_24h=False,
            market_cap_rank=rank,
            data_quality="full",
        )
    except Exception:
        return _DEGRADED
