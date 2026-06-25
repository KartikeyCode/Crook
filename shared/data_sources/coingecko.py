import httpx
from typing import Optional

CG_BASE = "https://api.coingecko.com/api/v3"
_coin_list: list = []  # cached after first call


async def get_coin_list() -> list:
    global _coin_list
    if _coin_list:
        return _coin_list
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{CG_BASE}/coins/list", params={"include_platform": "true"})
    if resp.status_code == 200:
        _coin_list = resp.json()
    return _coin_list


async def resolve_coin_id(token_address: str, chain: str, symbol: str = "") -> Optional[str]:
    platform = {"base": "base", "ethereum": "ethereum"}.get(chain, "ethereum")
    coins = await get_coin_list()
    addr_lower = token_address.lower()
    for coin in coins:
        if coin.get("platforms", {}).get(platform, "").lower() == addr_lower:
            return coin["id"]
    if symbol:
        sym_lower = symbol.lower()
        for coin in coins:
            if coin.get("symbol", "").lower() == sym_lower:
                return coin["id"]
    return None


async def get_coin_data(coin_id: str) -> Optional[dict]:
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "true",
        "developer_data": "false",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{CG_BASE}/coins/{coin_id}", params=params)
    return resp.json() if resp.status_code == 200 else None
