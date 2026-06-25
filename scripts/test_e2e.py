"""
E2E smoke test: sends a real AlphaRequest to the alpha_composer agent via CAP.
Requires all 5 agents running and .env populated with real keys + agent IDs.

Usage:
    python scripts/test_e2e.py [token_address] [chain]

Defaults to USDC on Base mainnet.
"""
import asyncio
import sys
import json
import os
from dotenv import load_dotenv
from croo import NegotiateOrderRequest, ListOptions

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.croo_client import make_client
from shared.schemas import AlphaRequest, AlphaResponse, Chain

# USDC on Base mainnet
DEFAULT_TOKEN = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
DEFAULT_CHAIN = Chain.BASE
DEFAULT_SYMBOL = "USDC"

POLL_INTERVAL = 3
MAX_WAIT = 180  # 3 minutes


async def run_e2e(token_address: str, chain: Chain, symbol: str):
    alpha_agent_id = os.environ["ALPHA_COMPOSER_AGENT_ID"]
    client = make_client(os.environ["ALPHA_COMPOSER_SDK_KEY"])

    req = AlphaRequest(token_address=token_address, chain=chain, token_symbol=symbol)
    print(f"\n[E2E] Requesting alpha for {symbol} ({token_address}) on {chain.value}")
    print(f"[E2E] Target agent: {alpha_agent_id}\n")

    neg = await client.negotiate_order(NegotiateOrderRequest(
        provider_agent_id=alpha_agent_id,
        requirements=req.model_dump_json(),
    ))
    neg_id = neg.negotiation_id
    print(f"[E2E] Negotiation created: {neg_id}")

    # Find order
    order_id = None
    for attempt in range(30):
        await asyncio.sleep(2)
        orders = await client.list_orders(ListOptions(role="requester", status="created"))
        for o in (orders.orders or []):
            if getattr(o, "negotiation_id", None) == neg_id:
                order_id = o.id
                break
        if order_id:
            break
    if not order_id:
        print("[E2E] FAIL: Timed out waiting for order creation")
        sys.exit(1)

    print(f"[E2E] Order created: {order_id}")
    await client.pay_order(order_id)
    print(f"[E2E] Order paid. Waiting for alpha report...")

    # Wait for completion
    for attempt in range(MAX_WAIT // POLL_INTERVAL):
        await asyncio.sleep(POLL_INTERVAL)
        orders = await client.list_orders(ListOptions(role="requester", status="completed"))
        for o in (orders.orders or []):
            if o.id == order_id:
                result = AlphaResponse.model_validate_json(o.deliverable_text)
                print("\n" + "=" * 60)
                print(f"ALPHA SCORE:      {result.alpha_score}/100")
                print(f"RECOMMENDATION:   {result.recommendation.upper()}")
                print(f"CONFIDENCE:       {result.confidence_pct}%")
                print(f"PARTIAL REPORT:   {result.partial_report}")
                print(f"COST:             ${result.sub_agent_costs_usdc} USDC")
                print("-" * 60)
                print(f"SUMMARY: {result.summary}")
                print("=" * 60)
                print("\n[E2E] PASS")
                return

    print("[E2E] FAIL: Timed out waiting for alpha report")
    sys.exit(1)


if __name__ == "__main__":
    token = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOKEN
    chain_str = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CHAIN.value
    symbol = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SYMBOL
    chain = Chain(chain_str)
    asyncio.run(run_e2e(token, chain, symbol))
