import os
import httpx

URLS = {
    "base": "https://api.basescan.org/api",
    "ethereum": "https://api.etherscan.io/api",
}


def _key(chain: str) -> str:
    return os.environ.get("BASESCAN_API_KEY" if chain == "base" else "ETHERSCAN_API_KEY", "")


async def get_token_transfers(token_address: str, chain: str, limit: int = 200) -> list:
    params = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": token_address,
        "sort": "desc",
        "apikey": _key(chain),
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(URLS[chain], params=params)
    data = resp.json()
    if data.get("status") != "1":
        return []
    return data.get("result", [])[:limit]
