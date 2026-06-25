from shared.data_sources.defillama import get_all_protocols
from shared.schemas import ProtocolHealthRequest, ProtocolHealthResponse

_DEGRADED = ProtocolHealthResponse(
    protocol_name="Unknown",
    tvl_usd=0.0,
    tvl_24h_change_pct=0.0,
    tvl_7d_change_pct=0.0,
    audit_status="unknown",
    auditor="unknown",
    chain_count=0,
    health_score=30,
    data_quality="degraded",
)


def compute_health_score(tvl_usd: float, tvl_24h_change: float, audited: bool) -> int:
    if tvl_usd >= 100_000_000:
        base = 70
    elif tvl_usd >= 10_000_000:
        base = 55
    elif tvl_usd >= 1_000_000:
        base = 40
    else:
        base = 20

    if tvl_24h_change >= 5:
        momentum = 10
    elif tvl_24h_change >= 0:
        momentum = 5
    elif tvl_24h_change >= -5:
        momentum = 0
    elif tvl_24h_change >= -20:
        momentum = -10
    else:
        momentum = -20

    audit_bonus = 15 if audited else 0
    return max(0, min(100, base + momentum + audit_bonus))


async def fetch_protocol_health(req: ProtocolHealthRequest) -> ProtocolHealthResponse:
    try:
        protocols = await get_all_protocols()
        addr_lower = req.token_address.lower()
        matched = next(
            (p for p in protocols if p.get("address") and addr_lower in p["address"].lower()),
            None,
        )
        if not matched:
            return _DEGRADED

        tvl = float(matched.get("tvl") or 0)
        tvl_1d = float(matched.get("change_1d") or 0)
        tvl_7d = float(matched.get("change_7d") or 0)
        audits = matched.get("audit_links") or []
        audited = len(audits) > 0
        chains = matched.get("chains") or []

        return ProtocolHealthResponse(
            protocol_name=matched.get("name", "Unknown"),
            tvl_usd=tvl,
            tvl_24h_change_pct=tvl_1d,
            tvl_7d_change_pct=tvl_7d,
            audit_status="audited" if audited else "unaudited",
            auditor="unknown",
            chain_count=len(chains),
            health_score=compute_health_score(tvl, tvl_1d, audited),
            data_quality="full",
        )
    except Exception:
        return _DEGRADED
