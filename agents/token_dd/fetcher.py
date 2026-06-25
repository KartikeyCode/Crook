from shared.data_sources.goplus import get_token_security
from shared.schemas import TokenDDRequest, TokenDDResponse

_DEGRADED = TokenDDResponse(
    is_honeypot=False,
    can_sell=True,
    ownership_renounced=False,
    contract_verified=False,
    liquidity_locked=False,
    buy_tax_pct=0.0,
    sell_tax_pct=0.0,
    risk_flags=["data_unavailable"],
    risk_level="medium",
    dd_score=30,
    data_quality="degraded",
)


def compute_risk_flags(
    is_honeypot: bool,
    buy_tax: float,
    sell_tax: float,
    ownership_renounced: bool,
) -> tuple[list[str], str]:
    flags = []
    if is_honeypot:
        flags.append("honeypot")
    if sell_tax > 10:
        flags.append("high_sell_tax")
    if buy_tax > 10:
        flags.append("high_buy_tax")
    if not ownership_renounced:
        flags.append("ownership_not_renounced")

    if is_honeypot or sell_tax > 50:
        level = "critical"
    elif len(flags) >= 3 or sell_tax > 10:
        level = "high"
    elif flags:
        level = "medium"
    else:
        level = "low"

    return flags, level


def compute_dd_score(
    is_honeypot: bool,
    buy_tax: float,
    sell_tax: float,
    ownership_renounced: bool,
    contract_verified: bool,
    liquidity_locked: bool,
) -> int:
    if is_honeypot:
        return 0
    score = 50
    if contract_verified:
        score += 15
    if ownership_renounced:
        score += 15
    if liquidity_locked:
        score += 10
    if buy_tax <= 3:
        score += 5
    if sell_tax <= 3:
        score += 5
    score -= max(0, int(sell_tax * 2))
    score -= max(0, int(buy_tax))
    return max(0, min(100, score))


async def fetch_token_dd(req: TokenDDRequest) -> TokenDDResponse:
    try:
        data = await get_token_security(req.token_address, req.chain.value)
        if not data:
            return _DEGRADED

        honeypot = data.get("is_honeypot", "0") == "1"
        can_sell = data.get("cannot_sell_all", "0") != "1"
        owner_renounced = data.get("owner_address", "") == ""
        verified = data.get("is_open_source", "0") == "1"
        lp_holders = data.get("lp_holders", [])
        liq_locked = any(h.get("is_locked", 0) == 1 for h in lp_holders)
        buy_tax = float(data.get("buy_tax", 0) or 0) * 100
        sell_tax = float(data.get("sell_tax", 0) or 0) * 100
        flags, level = compute_risk_flags(honeypot, buy_tax, sell_tax, owner_renounced)

        return TokenDDResponse(
            is_honeypot=honeypot,
            can_sell=can_sell,
            ownership_renounced=owner_renounced,
            contract_verified=verified,
            liquidity_locked=liq_locked,
            buy_tax_pct=round(buy_tax, 2),
            sell_tax_pct=round(sell_tax, 2),
            risk_flags=flags,
            risk_level=level,
            dd_score=compute_dd_score(honeypot, buy_tax, sell_tax, owner_renounced, verified, liq_locked),
            data_quality="full",
        )
    except Exception:
        return _DEGRADED
