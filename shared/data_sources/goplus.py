import httpx
from typing import Optional

CHAIN_IDS = {"ethereum": "1", "base": "8453"}
GOPLUS_BASE = "https://api.gopluslabs.io/api/v1"


async def get_token_security(token_address: str, chain: str) -> Optional[dict]:
    chain_id = CHAIN_IDS.get(chain, "1")
    params = {"contract_addresses": token_address.lower()}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{GOPLUS_BASE}/token_security/{chain_id}", params=params)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("code") != 1:
        return None
    result = data.get("result", {})
    return result.get(token_address.lower()) or result.get(token_address)
