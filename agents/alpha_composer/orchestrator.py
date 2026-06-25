import asyncio
import logging
import os
from croo import NegotiateOrderRequest, ListOptions
from shared.schemas import (
    AlphaRequest,
    AlphaResponse,
    WhaleTrackerRequest,
    WhaleTrackerResponse,
    ProtocolHealthRequest,
    ProtocolHealthResponse,
    TokenDDRequest,
    TokenDDResponse,
    SentimentRequest,
    SentimentResponse,
)
from agents.alpha_composer.scorer import compose_alpha

log = logging.getLogger("alpha-composer.orchestrator")

_DEGRADED_WHALE = WhaleTrackerResponse(
    large_movements=[], net_flow="neutral", movement_score=50,
    whale_count=0, data_quality="degraded",
)
_DEGRADED_HEALTH = ProtocolHealthResponse(
    protocol_name="Unknown", tvl_usd=0.0, tvl_24h_change_pct=0.0,
    tvl_7d_change_pct=0.0, audit_status="unknown", auditor="unknown",
    chain_count=0, health_score=30, data_quality="degraded",
)
_DEGRADED_DD = TokenDDResponse(
    is_honeypot=False, can_sell=True, ownership_renounced=False,
    contract_verified=False, liquidity_locked=False, buy_tax_pct=0.0,
    sell_tax_pct=0.0, risk_flags=["data_unavailable"], risk_level="medium",
    dd_score=30, data_quality="degraded",
)
_DEGRADED_SENTIMENT = SentimentResponse(
    sentiment="neutral", social_score=50, sentiment_votes_up_pct=50.0,
    sentiment_votes_down_pct=50.0, price_change_24h_pct=0.0,
    volume_spike_24h=False, market_cap_rank=None, data_quality="degraded",
)


async def _place_order(client, agent_id: str, requirements: str, timeout: float = 60.0) -> str | None:
    """Negotiate, pay, and wait for delivery. Returns deliverable text or None."""
    try:
        neg = await client.negotiate_order(NegotiateOrderRequest(
            provider_agent_id=agent_id,
            requirements=requirements,
        ))
        neg_id = neg.negotiation_id

        # Poll for the created order that matches this negotiation
        order_id = None
        for _ in range(30):
            await asyncio.sleep(2)
            orders = await client.list_orders(ListOptions(role="requester", status="created"))
            for o in (orders.orders or []):
                if getattr(o, "negotiation_id", None) == neg_id:
                    order_id = o.id
                    break
            if order_id:
                break

        if not order_id:
            log.warning(f"Timed out waiting for order from agent {agent_id}")
            return None

        await client.pay_order(order_id)

        # Wait for ORDER_COMPLETED — use polling since we can't share the stream here
        for _ in range(int(timeout / 2)):
            await asyncio.sleep(2)
            orders = await client.list_orders(ListOptions(role="requester", status="completed"))
            for o in (orders.orders or []):
                if o.id == order_id:
                    return o.deliverable_text
        log.warning(f"Timed out waiting for completion of order {order_id}")
        return None
    except Exception as e:
        log.error(f"Order to {agent_id} failed: {e}")
        return None


async def run_alpha(client, req: AlphaRequest) -> AlphaResponse:
    whale_agent_id = os.environ["WHALE_TRACKER_AGENT_ID"]
    health_agent_id = os.environ["PROTOCOL_HEALTH_AGENT_ID"]
    dd_agent_id = os.environ["TOKEN_DD_AGENT_ID"]
    sentiment_agent_id = os.environ["SENTIMENT_FUSION_AGENT_ID"]

    whale_req = WhaleTrackerRequest(token_address=req.token_address, chain=req.chain)
    health_req = ProtocolHealthRequest(token_address=req.token_address, chain=req.chain)
    dd_req = TokenDDRequest(token_address=req.token_address, chain=req.chain)
    sentiment_req = SentimentRequest(
        token_address=req.token_address, chain=req.chain, token_symbol=req.token_symbol
    )

    whale_text, health_text, dd_text, sentiment_text = await asyncio.gather(
        _place_order(client, whale_agent_id, whale_req.model_dump_json()),
        _place_order(client, health_agent_id, health_req.model_dump_json()),
        _place_order(client, dd_agent_id, dd_req.model_dump_json()),
        _place_order(client, sentiment_agent_id, sentiment_req.model_dump_json()),
    )

    def parse_or(text, model, fallback):
        if text:
            try:
                return model.model_validate_json(text)
            except Exception:
                pass
        return fallback

    whale = parse_or(whale_text, WhaleTrackerResponse, _DEGRADED_WHALE)
    health = parse_or(health_text, ProtocolHealthResponse, _DEGRADED_HEALTH)
    dd = parse_or(dd_text, TokenDDResponse, _DEGRADED_DD)
    sentiment = parse_or(sentiment_text, SentimentResponse, _DEGRADED_SENTIMENT)

    partial = any(r.data_quality == "degraded" for r in [whale, health, dd, sentiment])
    return compose_alpha(whale, health, dd, sentiment, partial=partial)
