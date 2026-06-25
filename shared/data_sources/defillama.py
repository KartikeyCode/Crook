import httpx
from typing import Optional

LLAMA_BASE = "https://api.llama.fi"


async def get_all_protocols() -> list:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{LLAMA_BASE}/protocols")
    return resp.json() if resp.status_code == 200 else []


async def get_protocol_tvl(slug: str) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{LLAMA_BASE}/protocol/{slug}")
    return resp.json() if resp.status_code == 200 else None
