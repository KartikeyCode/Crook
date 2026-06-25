from shared.data_sources.etherscan import get_token_transfers
from shared.schemas import WhaleTrackerRequest, WhaleTrackerResponse, LargeMovement

KNOWN_DEX_ADDRESSES = {
    "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24",
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad",
    "0x2626664c2603336e57b271c5c0b26f421741e481",
}
LARGE_THRESHOLD = 10_000  # token units

_DEGRADED = WhaleTrackerResponse(
    large_movements=[],
    net_flow="neutral",
    movement_score=50,
    whale_count=0,
    data_quality="degraded",
)


def classify_movement(tx: dict) -> str:
    return "sell" if tx.get("to", "").lower() in KNOWN_DEX_ADDRESSES else "buy"


def compute_movement_score(buy_count: int, sell_count: int, whale_count: int) -> int:
    if whale_count == 0:
        return 50
    buy_ratio = buy_count / whale_count
    base = int(buy_ratio * 100)
    volume_bonus = min(20, whale_count * 2)
    return max(0, min(100, base + volume_bonus - 10))


async def fetch_whale_data(req: WhaleTrackerRequest) -> WhaleTrackerResponse:
    try:
        txs = await get_token_transfers(req.token_address, req.chain.value)
        large = []
        for tx in txs:
            dec = int(tx.get("tokenDecimal", 18))
            value = int(tx.get("value", 0)) / (10 ** dec)
            if value >= LARGE_THRESHOLD:
                large.append(LargeMovement(
                    wallet=tx["from"],
                    amount_usd=value,
                    direction=classify_movement(tx),
                    tx_hash=tx["hash"],
                ))

        buy_count = sum(1 for m in large if m.direction == "buy")
        sell_count = len(large) - buy_count

        if not large:
            net_flow = "neutral"
        elif buy_count > sell_count:
            net_flow = "inflow"
        else:
            net_flow = "outflow"

        return WhaleTrackerResponse(
            large_movements=large[:10],
            net_flow=net_flow,
            movement_score=compute_movement_score(buy_count, sell_count, len(large)),
            whale_count=len(large),
            data_quality="full",
        )
    except Exception:
        return _DEGRADED
