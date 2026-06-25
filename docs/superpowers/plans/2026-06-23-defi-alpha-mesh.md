# DeFi Alpha Mesh — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 5 Python agents registered on CROO Agent Store that form a self-funding DeFi intelligence network, each earning USDC via CAP with zero infra cost.

**Architecture:** 4 specialist data-provider agents (whale-tracker, protocol-health, token-dd, sentiment-fusion) each listen for CAP orders via WebSocket and deliver JSON analysis using free public APIs. A 5th orchestrator agent (alpha-composer) acts as both provider to clients and requester to the 4 specialists, coordinating them with `asyncio.gather` and composing a unified alpha report.

**Tech Stack:** Python 3.10+, croo-sdk, pydantic v2, httpx, python-dotenv, pytest, pytest-asyncio, Docker, Oracle Cloud free tier

## Global Constraints

- Python >= 3.10 (uses `str | None` union syntax)
- All external data APIs must be free tier (no paid keys)
- Gas fees sponsored by CROO — only USDC for order payments
- Alpha Composer AA wallet must hold >= 8 USDC float before going live
- Each agent runs as standalone Docker container
- All JSON I/O validated with Pydantic v2 models
- No database — in-memory state only
- `pytest.ini` sets `asyncio_mode = auto`
- License: MIT (hackathon requirement)

---

## File Map

```
croo-defi-alpha-mesh/
├── pytest.ini
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── shared/
│   ├── __init__.py
│   ├── croo_client.py               # AgentClient factory
│   ├── schemas.py                   # All Pydantic I/O models
│   └── data_sources/
│       ├── __init__.py
│       ├── defillama.py             # DeFi Llama API (no key)
│       ├── etherscan.py             # Etherscan + Basescan (free key)
│       ├── goplus.py                # GoPlus Security (no key)
│       └── coingecko.py             # CoinGecko (no key, 30 req/min)
├── agents/
│   ├── protocol_health/
│   │   ├── __init__.py
│   │   ├── main.py                  # WebSocket provider loop
│   │   ├── fetcher.py               # DeFi Llama fetch + health scorer
│   │   └── Dockerfile
│   ├── whale_tracker/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── fetcher.py               # Etherscan fetch + movement scorer
│   │   └── Dockerfile
│   ├── token_dd/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── fetcher.py               # GoPlus fetch + DD scorer
│   │   └── Dockerfile
│   ├── sentiment_fusion/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── fetcher.py               # CoinGecko fetch + sentiment scorer
│   │   └── Dockerfile
│   └── alpha_composer/
│       ├── __init__.py
│       ├── main.py                  # Dual-role: provider + requester
│       ├── orchestrator.py          # asyncio.gather sub-order coordination
│       ├── scorer.py                # Alpha score computation + summary
│       └── Dockerfile
├── tests/
│   ├── conftest.py
│   ├── agents/
│   │   ├── protocol_health/
│   │   │   └── test_scorer.py
│   │   ├── whale_tracker/
│   │   │   └── test_scorer.py
│   │   ├── token_dd/
│   │   │   └── test_scorer.py
│   │   ├── sentiment_fusion/
│   │   │   └── test_scorer.py
│   │   └── alpha_composer/
│   │       └── test_scorer.py
└── scripts/
    └── test_e2e.py                  # Places real order, prints result
```

---

## Task 1: Scaffold + Shared Infrastructure

**Files:**
- Create: `pytest.ini`
- Create: `requirements.txt`
- Create: `shared/__init__.py`
- Create: `shared/croo_client.py`
- Create: `shared/schemas.py`
- Create: `shared/data_sources/__init__.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: `make_client(sdk_key?)→AgentClient`, all Pydantic request/response models used by Tasks 2-6

- [ ] **Step 1: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 2: Create `requirements.txt`**

```
croo-sdk>=0.1.0
pydantic>=2.0.0
httpx>=0.27.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: no errors. Verify with `python -c "from croo import AgentClient; print('ok')"`.

- [ ] **Step 4: Create `shared/croo_client.py`**

```python
import os
from croo import Config, AgentClient

def make_client(sdk_key: str | None = None) -> AgentClient:
    config = Config(
        base_url=os.environ["CROO_API_URL"],
        ws_url=os.environ["CROO_WS_URL"],
    )
    return AgentClient(config, sdk_key or os.environ["CROO_SDK_KEY"])
```

- [ ] **Step 5: Create `shared/schemas.py`**

```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class Chain(str, Enum):
    BASE = "base"
    ETHEREUM = "ethereum"

# --- Whale Tracker ---
class WhaleTrackerRequest(BaseModel):
    token_address: str
    chain: Chain
    lookback_hours: int = 24

class LargeMovement(BaseModel):
    wallet: str
    amount_usd: float
    direction: str
    tx_hash: str

class WhaleTrackerResponse(BaseModel):
    large_movements: list[LargeMovement]
    net_flow: str
    movement_score: int
    whale_count: int
    data_quality: str

# --- Protocol Health ---
class ProtocolHealthRequest(BaseModel):
    token_address: str
    chain: Chain

class ProtocolHealthResponse(BaseModel):
    protocol_name: str
    tvl_usd: float
    tvl_24h_change_pct: float
    tvl_7d_change_pct: float
    audit_status: str
    auditor: str
    chain_count: int
    health_score: int
    data_quality: str

# --- Token DD ---
class TokenDDRequest(BaseModel):
    token_address: str
    chain: Chain

class TokenDDResponse(BaseModel):
    is_honeypot: bool
    can_sell: bool
    ownership_renounced: bool
    contract_verified: bool
    liquidity_locked: bool
    buy_tax_pct: float
    sell_tax_pct: float
    risk_flags: list[str]
    risk_level: str
    dd_score: int
    data_quality: str

# --- Sentiment Fusion ---
class SentimentRequest(BaseModel):
    token_address: str
    token_symbol: str = ""
    chain: Chain

class SentimentResponse(BaseModel):
    sentiment: str
    social_score: int
    sentiment_votes_up_pct: float
    sentiment_votes_down_pct: float
    price_change_24h_pct: float
    volume_spike_24h: bool
    market_cap_rank: Optional[int]
    data_quality: str

# --- Alpha Composer ---
class AlphaRequest(BaseModel):
    token_address: str
    chain: Chain
    token_symbol: str = ""

class AlphaResponse(BaseModel):
    alpha_score: int
    recommendation: str
    confidence_pct: int
    whale_activity: dict
    protocol_health: dict
    token_dd: dict
    sentiment: dict
    summary: str
    generated_at: str
    sub_agent_costs_usdc: float
    partial_report: bool
```

- [ ] **Step 6: Create empty `__init__.py` files**

```bash
mkdir -p agents shared shared/data_sources tests/agents/protocol_health
mkdir -p tests/agents/whale_tracker tests/agents/token_dd
mkdir -p tests/agents/sentiment_fusion tests/agents/alpha_composer
touch agents/__init__.py shared/__init__.py shared/data_sources/__init__.py
touch tests/__init__.py tests/agents/__init__.py
touch tests/agents/protocol_health/__init__.py tests/agents/whale_tracker/__init__.py
touch tests/agents/token_dd/__init__.py tests/agents/sentiment_fusion/__init__.py
touch tests/agents/alpha_composer/__init__.py
```

- [ ] **Step 7: Create `tests/conftest.py`**

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
```

- [ ] **Step 8: Run pytest to verify zero-error baseline**

```bash
pytest tests/ -v
```

Expected: `no tests ran` (no test files yet). Exit code 0. If import errors appear, fix path issues before continuing.

- [ ] **Step 9: Commit**

```bash
git init
git add .
git commit -m "feat: scaffold shared infrastructure and schemas"
```

---

## Task 2: Protocol Health Agent

**Files:**
- Create: `shared/data_sources/defillama.py`
- Create: `agents/protocol_health/__init__.py`
- Create: `agents/protocol_health/fetcher.py`
- Create: `agents/protocol_health/main.py`
- Create: `agents/protocol_health/Dockerfile`
- Create: `tests/agents/protocol_health/test_scorer.py`

**Interfaces:**
- Consumes: `shared/schemas.py → ProtocolHealthRequest, ProtocolHealthResponse`
- Produces: `fetch_protocol_health(req: ProtocolHealthRequest) → ProtocolHealthResponse`, `compute_health_score(tvl_usd, tvl_24h_change, audited) → int` (used by test)

- [ ] **Step 1: Write failing tests for `compute_health_score`**

Create `tests/agents/protocol_health/test_scorer.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from agents.protocol_health.fetcher import compute_health_score

def test_high_tvl_audited_scores_high():
    score = compute_health_score(tvl_usd=500_000_000, tvl_24h_change=2.0, audited=True)
    assert score >= 80

def test_low_tvl_crashing_unaudited_scores_low():
    score = compute_health_score(tvl_usd=50_000, tvl_24h_change=-25.0, audited=False)
    assert score <= 20

def test_score_always_bounded_0_to_100():
    assert 0 <= compute_health_score(0, -100.0, False) <= 100
    assert 0 <= compute_health_score(1_000_000_000, 100.0, True) <= 100

def test_audit_bonus_makes_difference():
    without = compute_health_score(tvl_usd=10_000_000, tvl_24h_change=0.0, audited=False)
    with_audit = compute_health_score(tvl_usd=10_000_000, tvl_24h_change=0.0, audited=True)
    assert with_audit > without
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/agents/protocol_health/test_scorer.py -v
```

Expected: `ModuleNotFoundError: No module named 'agents'`. That's correct — implementation missing.

- [ ] **Step 3: Create `shared/data_sources/defillama.py`**

```python
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
```

- [ ] **Step 4: Create `agents/protocol_health/fetcher.py`**

```python
from shared.data_sources.defillama import get_all_protocols
from shared.schemas import ProtocolHealthRequest, ProtocolHealthResponse

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

_DEGRADED = ProtocolHealthResponse(
    protocol_name="Unknown", tvl_usd=0.0, tvl_24h_change_pct=0.0,
    tvl_7d_change_pct=0.0, audit_status="unknown", auditor="unknown",
    chain_count=0, health_score=30, data_quality="degraded",
)

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
```

- [ ] **Step 5: Create `agents/protocol_health/__init__.py`** (empty)

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/agents/protocol_health/test_scorer.py -v
```

Expected: 4 PASSED.

- [ ] **Step 7: Create `agents/protocol_health/main.py`**

```python
import asyncio
import json
import logging
import os
from dotenv import load_dotenv
from croo import EventType, DeliverOrderRequest, DeliverableType, ListOptions
from shared.croo_client import make_client
from shared.schemas import ProtocolHealthRequest
from agents.protocol_health.fetcher import fetch_protocol_health

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("protocol-health")

async def deliver(client, order_id: str, requirements: str):
    try:
        req = ProtocolHealthRequest.model_validate_json(requirements)
        result = await fetch_protocol_health(req)
        await client.deliver_order(order_id, DeliverOrderRequest(
            deliverable_type=DeliverableType.TEXT,
            deliverable_text=result.model_dump_json(),
        ))
        log.info(f"Delivered order {order_id}")
    except Exception as e:
        log.error(f"Failed order {order_id}: {e}")
        await client.reject_order(order_id, str(e))

async def main():
    client = make_client()
    stream = await client.connect_websocket()

    orphaned = await client.list_orders(ListOptions(role="provider", status="paid"))
    for order in (orphaned.orders or []):
        log.info(f"Recovering orphaned order {order.id}")
        asyncio.create_task(deliver(client, order.id, order.requirements))

    stream.on(EventType.NEGOTIATION_CREATED,
              lambda e: asyncio.create_task(client.accept_negotiation(e.negotiation_id)))
    stream.on(EventType.ORDER_PAID,
              lambda e: asyncio.create_task(deliver(client, e.order_id, e.requirements)))

    log.info("Protocol Health agent listening...")
    await stream.listen()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 8: Create `agents/protocol_health/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY agents/protocol_health/ ./agents/protocol_health/
COPY agents/__init__.py ./agents/__init__.py
CMD ["python", "-m", "agents.protocol_health.main"]
```

- [ ] **Step 9: Commit**

```bash
git add .
git commit -m "feat: add protocol-health agent with DeFi Llama integration"
```

---

## Task 3: Whale Tracker Agent

**Files:**
- Create: `shared/data_sources/etherscan.py`
- Create: `agents/whale_tracker/__init__.py`
- Create: `agents/whale_tracker/fetcher.py`
- Create: `agents/whale_tracker/main.py`
- Create: `agents/whale_tracker/Dockerfile`
- Create: `tests/agents/whale_tracker/test_scorer.py`

**Interfaces:**
- Consumes: `shared/schemas.py → WhaleTrackerRequest, WhaleTrackerResponse, LargeMovement`
- Produces: `fetch_whale_data(req) → WhaleTrackerResponse`, `compute_movement_score(buy, sell, total) → int`, `classify_movement(tx) → str`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/whale_tracker/test_scorer.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from agents.whale_tracker.fetcher import compute_movement_score, classify_movement

def test_all_buys_scores_high():
    assert compute_movement_score(buy_count=10, sell_count=0, whale_count=10) >= 80

def test_all_sells_scores_low():
    assert compute_movement_score(buy_count=0, sell_count=10, whale_count=10) <= 20

def test_no_whales_returns_neutral_50():
    assert compute_movement_score(0, 0, 0) == 50

def test_score_bounded_0_to_100():
    assert 0 <= compute_movement_score(1000, 0, 1000) <= 100
    assert 0 <= compute_movement_score(0, 1000, 1000) <= 100

def test_known_dex_classified_as_sell():
    tx = {"to": "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24"}
    assert classify_movement(tx) == "sell"

def test_unknown_address_classified_as_buy():
    tx = {"to": "0x1234567890abcdef1234567890abcdef12345678"}
    assert classify_movement(tx) == "buy"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/agents/whale_tracker/test_scorer.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `shared/data_sources/etherscan.py`**

```python
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
```

- [ ] **Step 4: Create `agents/whale_tracker/fetcher.py`**

```python
from shared.data_sources.etherscan import get_token_transfers
from shared.schemas import WhaleTrackerRequest, WhaleTrackerResponse, LargeMovement

KNOWN_DEX_ADDRESSES = {
    "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24",
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad",
    "0x2626664c2603336e57b271c5c0b26f421741e481",
}
LARGE_THRESHOLD = 10_000  # token units (not USD — avoids need for price oracle)

def classify_movement(tx: dict) -> str:
    return "sell" if tx.get("to", "").lower() in KNOWN_DEX_ADDRESSES else "buy"

def compute_movement_score(buy_count: int, sell_count: int, whale_count: int) -> int:
    if whale_count == 0:
        return 50
    buy_ratio = buy_count / whale_count
    base = int(buy_ratio * 100)
    volume_bonus = min(20, whale_count * 2)
    return max(0, min(100, base + volume_bonus - 10))

_DEGRADED = WhaleTrackerResponse(
    large_movements=[], net_flow="neutral",
    movement_score=50, whale_count=0, data_quality="degraded",
)

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

        if len(large) == 0:
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
```

- [ ] **Step 5: Create `agents/whale_tracker/__init__.py`** (empty)

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/agents/whale_tracker/test_scorer.py -v
```

Expected: 6 PASSED.

- [ ] **Step 7: Create `agents/whale_tracker/main.py`**

```python
import asyncio
import logging
import os
from dotenv import load_dotenv
from croo import EventType, DeliverOrderRequest, DeliverableType, ListOptions
from shared.croo_client import make_client
from shared.schemas import WhaleTrackerRequest
from agents.whale_tracker.fetcher import fetch_whale_data

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("whale-tracker")

async def deliver(client, order_id: str, requirements: str):
    try:
        req = WhaleTrackerRequest.model_validate_json(requirements)
        result = await fetch_whale_data(req)
        await client.deliver_order(order_id, DeliverOrderRequest(
            deliverable_type=DeliverableType.TEXT,
            deliverable_text=result.model_dump_json(),
        ))
        log.info(f"Delivered order {order_id}")
    except Exception as e:
        log.error(f"Failed order {order_id}: {e}")
        await client.reject_order(order_id, str(e))

async def main():
    client = make_client()
    stream = await client.connect_websocket()

    orphaned = await client.list_orders(ListOptions(role="provider", status="paid"))
    for order in (orphaned.orders or []):
        asyncio.create_task(deliver(client, order.id, order.requirements))

    stream.on(EventType.NEGOTIATION_CREATED,
              lambda e: asyncio.create_task(client.accept_negotiation(e.negotiation_id)))
    stream.on(EventType.ORDER_PAID,
              lambda e: asyncio.create_task(deliver(client, e.order_id, e.requirements)))

    log.info("Whale Tracker agent listening...")
    await stream.listen()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 8: Create `agents/whale_tracker/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY agents/whale_tracker/ ./agents/whale_tracker/
COPY agents/__init__.py ./agents/__init__.py
CMD ["python", "-m", "agents.whale_tracker.main"]
```

- [ ] **Step 9: Commit**

```bash
git add .
git commit -m "feat: add whale-tracker agent with Etherscan integration"
```

---

## Task 4: Token DD Agent

**Files:**
- Create: `shared/data_sources/goplus.py`
- Create: `agents/token_dd/__init__.py`
- Create: `agents/token_dd/fetcher.py`
- Create: `agents/token_dd/main.py`
- Create: `agents/token_dd/Dockerfile`
- Create: `tests/agents/token_dd/test_scorer.py`

**Interfaces:**
- Consumes: `shared/schemas.py → TokenDDRequest, TokenDDResponse`
- Produces: `fetch_token_dd(req) → TokenDDResponse`, `compute_risk_flags(honeypot, buy_tax, sell_tax, renounced) → tuple[list[str], str]`, `compute_dd_score(...) → int`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/token_dd/test_scorer.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from agents.token_dd.fetcher import compute_risk_flags, compute_dd_score

def test_honeypot_is_critical():
    flags, level = compute_risk_flags(True, 2.0, 2.0, True)
    assert "honeypot" in flags
    assert level == "critical"

def test_high_sell_tax_flagged_as_high_risk():
    flags, level = compute_risk_flags(False, 2.0, 15.0, True)
    assert "high_sell_tax" in flags
    assert level in ("high", "medium")

def test_clean_token_is_low_risk():
    flags, level = compute_risk_flags(False, 2.0, 2.0, True)
    assert level == "low"

def test_honeypot_scores_zero():
    assert compute_dd_score(True, 0, 0, True, True, True) == 0

def test_perfect_token_scores_above_80():
    assert compute_dd_score(False, 2.0, 2.0, True, True, True) >= 80

def test_dd_score_bounded_0_to_100():
    assert 0 <= compute_dd_score(False, 0, 0, True, True, True) <= 100
    assert 0 <= compute_dd_score(False, 50, 99, False, False, False) <= 100
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/agents/token_dd/test_scorer.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `shared/data_sources/goplus.py`**

```python
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
```

- [ ] **Step 4: Create `agents/token_dd/fetcher.py`**

```python
from shared.data_sources.goplus import get_token_security
from shared.schemas import TokenDDRequest, TokenDDResponse

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

_DEGRADED = TokenDDResponse(
    is_honeypot=False, can_sell=True, ownership_renounced=False,
    contract_verified=False, liquidity_locked=False, buy_tax_pct=0.0,
    sell_tax_pct=0.0, risk_flags=["data_unavailable"], risk_level="medium",
    dd_score=30, data_quality="degraded",
)

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
            is_honeypot=honeypot, can_sell=can_sell,
            ownership_renounced=owner_renounced, contract_verified=verified,
            liquidity_locked=liq_locked, buy_tax_pct=round(buy_tax, 2),
            sell_tax_pct=round(sell_tax, 2), risk_flags=flags, risk_level=level,
            dd_score=compute_dd_score(honeypot, buy_tax, sell_tax, owner_renounced, verified, liq_locked),
            data_quality="full",
        )
    except Exception:
        return _DEGRADED
```

- [ ] **Step 5: Create `agents/token_dd/__init__.py`** (empty)

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/agents/token_dd/test_scorer.py -v
```

Expected: 6 PASSED.

- [ ] **Step 7: Create `agents/token_dd/main.py`**

```python
import asyncio
import logging
import os
from dotenv import load_dotenv
from croo import EventType, DeliverOrderRequest, DeliverableType, ListOptions
from shared.croo_client import make_client
from shared.schemas import TokenDDRequest
from agents.token_dd.fetcher import fetch_token_dd

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("token-dd")

async def deliver(client, order_id: str, requirements: str):
    try:
        req = TokenDDRequest.model_validate_json(requirements)
        result = await fetch_token_dd(req)
        await client.deliver_order(order_id, DeliverOrderRequest(
            deliverable_type=DeliverableType.TEXT,
            deliverable_text=result.model_dump_json(),
        ))
        log.info(f"Delivered order {order_id}")
    except Exception as e:
        log.error(f"Failed order {order_id}: {e}")
        await client.reject_order(order_id, str(e))

async def main():
    client = make_client()
    stream = await client.connect_websocket()

    orphaned = await client.list_orders(ListOptions(role="provider", status="paid"))
    for order in (orphaned.orders or []):
        asyncio.create_task(deliver(client, order.id, order.requirements))

    stream.on(EventType.NEGOTIATION_CREATED,
              lambda e: asyncio.create_task(client.accept_negotiation(e.negotiation_id)))
    stream.on(EventType.ORDER_PAID,
              lambda e: asyncio.create_task(deliver(client, e.order_id, e.requirements)))

    log.info("Token DD agent listening...")
    await stream.listen()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 8: Create `agents/token_dd/Dockerfile`** (same pattern as Task 2, swap agent name)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY agents/token_dd/ ./agents/token_dd/
COPY agents/__init__.py ./agents/__init__.py
CMD ["python", "-m", "agents.token_dd.main"]
```

- [ ] **Step 9: Commit**

```bash
git add .
git commit -m "feat: add token-dd agent with GoPlus Security integration"
```

---

## Task 5: Sentiment Fusion Agent

**Files:**
- Create: `shared/data_sources/coingecko.py`
- Create: `agents/sentiment_fusion/__init__.py`
- Create: `agents/sentiment_fusion/fetcher.py`
- Create: `agents/sentiment_fusion/main.py`
- Create: `agents/sentiment_fusion/Dockerfile`
- Create: `tests/agents/sentiment_fusion/test_scorer.py`

**Interfaces:**
- Consumes: `shared/schemas.py → SentimentRequest, SentimentResponse`
- Produces: `fetch_sentiment(req) → SentimentResponse`, `compute_sentiment_label(votes_up_pct, price_change_24h) → str`, `compute_social_score(votes_up_pct, price_change_24h, rank) → int`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/sentiment_fusion/test_scorer.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from agents.sentiment_fusion.fetcher import compute_sentiment_label, compute_social_score

def test_high_votes_positive_price_is_bullish():
    assert compute_sentiment_label(75.0, 5.0) == "bullish"

def test_low_votes_crashing_price_is_bearish():
    assert compute_sentiment_label(30.0, -10.0) == "bearish"

def test_mixed_signals_is_neutral():
    assert compute_sentiment_label(50.0, 1.0) == "neutral"

def test_social_score_bounded_0_to_100():
    assert 0 <= compute_social_score(100.0, 10.0, 1) <= 100
    assert 0 <= compute_social_score(0.0, -20.0, None) <= 100

def test_top_100_rank_adds_bonus():
    without = compute_social_score(60.0, 0.0, None)
    with_rank = compute_social_score(60.0, 0.0, 50)
    assert with_rank > without
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/agents/sentiment_fusion/test_scorer.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `shared/data_sources/coingecko.py`**

```python
import httpx
from typing import Optional

CG_BASE = "https://api.coingecko.com/api/v3"
_coin_list: list = []  # in-memory cache, populated once on first call

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
    params = {"localization": "false", "tickers": "false",
               "market_data": "true", "community_data": "true", "developer_data": "false"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{CG_BASE}/coins/{coin_id}", params=params)
    return resp.json() if resp.status_code == 200 else None
```

- [ ] **Step 4: Create `agents/sentiment_fusion/fetcher.py`**

```python
from typing import Optional
from shared.data_sources.coingecko import resolve_coin_id, get_coin_data
from shared.schemas import SentimentRequest, SentimentResponse

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

_DEGRADED = SentimentResponse(
    sentiment="neutral", social_score=50, sentiment_votes_up_pct=50.0,
    sentiment_votes_down_pct=50.0, price_change_24h_pct=0.0,
    volume_spike_24h=False, market_cap_rank=None, data_quality="degraded",
)

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
            volume_spike_24h=False,  # simplified: avoid extra API call
            market_cap_rank=rank,
            data_quality="full",
        )
    except Exception:
        return _DEGRADED
```

- [ ] **Step 5: Create `agents/sentiment_fusion/__init__.py`** (empty)

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/agents/sentiment_fusion/test_scorer.py -v
```

Expected: 5 PASSED.

- [ ] **Step 7: Create `agents/sentiment_fusion/main.py`**

```python
import asyncio
import logging
import os
from dotenv import load_dotenv
from croo import EventType, DeliverOrderRequest, DeliverableType, ListOptions
from shared.croo_client import make_client
from shared.schemas import SentimentRequest
from agents.sentiment_fusion.fetcher import fetch_sentiment

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("sentiment-fusion")

async def deliver(client, order_id: str, requirements: str):
    try:
        req = SentimentRequest.model_validate_json(requirements)
        result = await fetch_sentiment(req)
        await client.deliver_order(order_id, DeliverOrderRequest(
            deliverable_type=DeliverableType.TEXT,
            deliverable_text=result.model_dump_json(),
        ))
        log.info(f"Delivered order {order_id}")
    except Exception as e:
        log.error(f"Failed order {order_id}: {e}")
        await client.reject_order(order_id, str(e))

async def main():
    client = make_client()
    stream = await client.connect_websocket()

    orphaned = await client.list_orders(ListOptions(role="provider", status="paid"))
    for order in (orphaned.orders or []):
        asyncio.create_task(deliver(client, order.id, order.requirements))

    stream.on(EventType.NEGOTIATION_CREATED,
              lambda e: asyncio.create_task(client.accept_negotiation(e.negotiation_id)))
    stream.on(EventType.ORDER_PAID,
              lambda e: asyncio.create_task(deliver(client, e.order_id, e.requirements)))

    log.info("Sentiment Fusion agent listening...")
    await stream.listen()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 8: Create `agents/sentiment_fusion/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY agents/sentiment_fusion/ ./agents/sentiment_fusion/
COPY agents/__init__.py ./agents/__init__.py
CMD ["python", "-m", "agents.sentiment_fusion.main"]
```

- [ ] **Step 9: Run ALL tests to confirm no regressions**

```bash
pytest tests/ -v
```

Expected: 21 PASSED (4 + 6 + 6 + 5).

- [ ] **Step 10: Commit**

```bash
git add .
git commit -m "feat: add sentiment-fusion agent with CoinGecko integration"
```

---

## Task 6: Alpha Composer Orchestrator

**Files:**
- Create: `agents/alpha_composer/__init__.py`
- Create: `agents/alpha_composer/scorer.py`
- Create: `agents/alpha_composer/orchestrator.py`
- Create: `agents/alpha_composer/main.py`
- Create: `agents/alpha_composer/Dockerfile`
- Create: `tests/agents/alpha_composer/test_scorer.py`

**Interfaces:**
- Consumes: CROO sub-agent service IDs from env vars; `shared/schemas.py → AlphaRequest, AlphaResponse`
- Produces: `compute_alpha_score(whale, health, dd, sentiment) → tuple[int,int]`, `score_to_recommendation(score, dd) → str`, `build_summary(...) → str`

**Assumption:** The CROO SDK's Order object includes a `negotiation_id` field. If not, the `hire()` method falls back to polling `list_orders` filtered client-side by comparing creation time.

- [ ] **Step 1: Write failing tests for scorer**

Create `tests/agents/alpha_composer/test_scorer.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from agents.alpha_composer.scorer import compute_alpha_score, score_to_recommendation, build_summary

W_BULL = {"movement_score": 80, "net_flow": "inflow", "whale_count": 5}
W_BEAR = {"movement_score": 20, "net_flow": "outflow", "whale_count": 5}
H_GOOD = {"health_score": 85, "tvl_24h_change_pct": 5.0, "tvl_usd": 5_000_000}
DD_OK   = {"dd_score": 90, "is_honeypot": False, "risk_level": "low"}
DD_HP   = {"dd_score": 0,  "is_honeypot": True,  "risk_level": "critical"}
S_BULL  = {"social_score": 75, "sentiment": "bullish", "sentiment_votes_up_pct": 75}
UNAVAIL = {"status": "unavailable"}

def test_all_bullish_signals_score_above_70():
    score, conf = compute_alpha_score(W_BULL, H_GOOD, DD_OK, S_BULL)
    assert score >= 70
    assert conf == 100

def test_honeypot_overrides_to_zero():
    score, conf = compute_alpha_score(W_BULL, H_GOOD, DD_HP, S_BULL)
    assert score == 0
    assert conf >= 90

def test_all_bearish_scores_below_40():
    score, conf = compute_alpha_score(W_BEAR, H_GOOD, DD_OK, S_BULL)
    assert score < 80  # bears pull score down

def test_two_unavailable_gives_50_confidence():
    score, conf = compute_alpha_score(W_BULL, UNAVAIL, DD_OK, UNAVAIL)
    assert conf == 50

def test_recommendation_accumulate_at_75():
    assert score_to_recommendation(75, DD_OK) == "accumulate"

def test_recommendation_avoid_honeypot():
    assert score_to_recommendation(80, DD_HP) == "avoid"

def test_recommendation_hold_at_55():
    assert score_to_recommendation(55, DD_OK) == "hold"

def test_recommendation_watch_at_35():
    assert score_to_recommendation(35, DD_OK) == "watch"

def test_recommendation_avoid_below_30():
    assert score_to_recommendation(20, DD_OK) == "avoid"

def test_summary_contains_uppercase_recommendation():
    summary = build_summary(75, W_BULL, H_GOOD, DD_OK, S_BULL)
    assert "ACCUMULATE" in summary

def test_summary_flags_honeypot():
    summary = build_summary(0, W_BULL, H_GOOD, DD_HP, S_BULL)
    assert "HONEYPOT" in summary.upper()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/agents/alpha_composer/test_scorer.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `agents/alpha_composer/scorer.py`**

```python
def compute_alpha_score(whale: dict, health: dict, dd: dict, sentiment: dict) -> tuple[int, int]:
    if dd.get("is_honeypot") or dd.get("risk_level") == "critical":
        return 0, 95

    scores: list[tuple[int, float]] = []

    if whale.get("status") != "unavailable":
        w = whale.get("movement_score", 50)
        flow = {"inflow": 10, "outflow": -10, "neutral": 0}.get(whale.get("net_flow", "neutral"), 0)
        scores.append((min(100, max(0, w + flow)), 0.25))

    if health.get("status") != "unavailable":
        h = health.get("health_score", 50)
        tvl = health.get("tvl_24h_change_pct", 0)
        momentum = min(10, max(-10, int(tvl)))
        scores.append((min(100, max(0, h + momentum)), 0.25))

    if dd.get("status") != "unavailable":
        scores.append((dd.get("dd_score", 50), 0.30))

    if sentiment.get("status") != "unavailable":
        s = sentiment.get("social_score", 50)
        adj = {"bullish": 10, "bearish": -10, "neutral": 0}.get(sentiment.get("sentiment", "neutral"), 0)
        scores.append((min(100, max(0, s + adj)), 0.20))

    if not scores:
        return 50, 0

    total_w = sum(w for _, w in scores)
    alpha = int(sum(s * w for s, w in scores) / total_w)
    confidence = int(len(scores) / 4 * 100)
    return alpha, confidence


def score_to_recommendation(alpha_score: int, dd: dict) -> str:
    if dd.get("is_honeypot") or dd.get("risk_level") == "critical":
        return "avoid"
    if alpha_score >= 70:
        return "accumulate"
    if alpha_score >= 50:
        return "hold"
    if alpha_score >= 30:
        return "watch"
    return "avoid"


def build_summary(alpha_score: int, whale: dict, health: dict, dd: dict, sentiment: dict) -> str:
    parts = []

    if whale.get("net_flow") == "inflow":
        parts.append(f"Whale inflow ({whale.get('whale_count', 0)} large buys)")
    elif whale.get("net_flow") == "outflow":
        parts.append(f"Whale outflow ({whale.get('whale_count', 0)} large sells)")

    tvl = health.get("tvl_usd", 0)
    if tvl > 0:
        chg = health.get("tvl_24h_change_pct", 0)
        parts.append(f"TVL ${tvl:,.0f} ({chg:+.1f}% 24h)")

    if dd.get("is_honeypot"):
        parts.append("HONEYPOT DETECTED — do not buy")
    elif dd.get("risk_level") == "low":
        parts.append("Contract clean")

    sent = sentiment.get("sentiment", "neutral")
    if sent != "neutral":
        up = sentiment.get("sentiment_votes_up_pct", 50)
        parts.append(f"Sentiment {sent} ({up:.0f}% bullish)")

    rec = score_to_recommendation(alpha_score, dd)
    return f"{'. '.join(parts)}. Score {alpha_score}/100 — {rec.upper()}."
```

- [ ] **Step 4: Run tests to verify scorer passes**

```bash
pytest tests/agents/alpha_composer/test_scorer.py -v
```

Expected: 11 PASSED.

- [ ] **Step 5: Create `agents/alpha_composer/orchestrator.py`**

```python
import asyncio
import json
import logging
from croo import EventType, NegotiateOrderRequest, ListOptions

log = logging.getLogger("alpha-composer.orchestrator")

class AlphaOrchestrator:
    def __init__(self, client, service_ids: dict[str, str]):
        self.client = client
        self.service_ids = service_ids
        # order_id → (asyncio.Event, result_dict)
        self._sub_orders: dict[str, tuple[asyncio.Event, dict]] = {}

    def register_handlers(self, stream) -> None:
        # ORDER_CREATED not handled here — hire() calls pay_order() manually after polling
        stream.on(EventType.ORDER_COMPLETED, self._on_completed)
        stream.on(EventType.ORDER_EXPIRED,   self._on_failed)
        stream.on(EventType.ORDER_REJECTED,  self._on_failed)

    async def _on_completed(self, e) -> None:
        if e.order_id not in self._sub_orders:
            return
        ev, result = self._sub_orders[e.order_id]
        try:
            delivery = await self.client.get_delivery(e.order_id)
            result["data"] = json.loads(delivery.deliverable_text)
        except Exception as exc:
            result["data"] = {"status": "unavailable", "reason": str(exc)}
        ev.set()

    async def _on_failed(self, e) -> None:
        if e.order_id not in self._sub_orders:
            return
        ev, result = self._sub_orders[e.order_id]
        result["data"] = {"status": "unavailable", "reason": "order_failed_or_expired"}
        ev.set()

    async def hire(self, service_key: str, requirements: dict, timeout: int = 540) -> dict:
        service_id = self.service_ids[service_key]
        ev = asyncio.Event()
        result: dict = {}

        neg = await self.client.negotiate_order(NegotiateOrderRequest(
            service_id=service_id,
            requirements=json.dumps(requirements),
        ))
        neg_id = neg.negotiation_id

        # Poll list_orders to find the order created from this negotiation.
        # Provider accepts within a few seconds for a live agent.
        order_id: str | None = None
        for _ in range(30):
            await asyncio.sleep(2)
            orders_resp = await self.client.list_orders(
                ListOptions(role="requester", status="created", page_size=50)
            )
            for order in (orders_resp.orders or []):
                # Match by negotiation_id if field exists, else take oldest untracked created order
                if getattr(order, "negotiation_id", None) == neg_id:
                    order_id = order.id
                    break
                if order.id not in self._sub_orders:
                    order_id = order.id
                    break
            if order_id:
                break

        if not order_id:
            log.warning(f"Order not created for negotiation {neg_id} after 60s")
            return {"status": "unavailable", "reason": "order_not_created"}

        self._sub_orders[order_id] = (ev, result)
        await self.client.pay_order(order_id)

        try:
            await asyncio.wait_for(ev.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            result["data"] = {"status": "unavailable", "reason": "client_timeout"}

        self._sub_orders.pop(order_id, None)
        return result.get("data", {"status": "unavailable", "reason": "unknown"})

    async def run(self, token_address: str, chain: str, token_symbol: str = "") -> dict:
        base = {"token_address": token_address, "chain": chain}
        whale, health, dd, sentiment = await asyncio.gather(
            self.hire("whale",     {**base, "lookback_hours": 24}),
            self.hire("health",    base),
            self.hire("dd",        base),
            self.hire("sentiment", {**base, "token_symbol": token_symbol}),
            return_exceptions=True,
        )

        def safe(r):
            return r if not isinstance(r, Exception) else {"status": "unavailable", "reason": str(r)}

        return safe(whale), safe(health), safe(dd), safe(sentiment)
```

- [ ] **Step 6: Create `agents/alpha_composer/__init__.py`** (empty)

- [ ] **Step 7: Create `agents/alpha_composer/main.py`**

```python
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from croo import EventType, DeliverOrderRequest, DeliverableType, ListOptions
from shared.croo_client import make_client
from shared.schemas import AlphaRequest, AlphaResponse
from agents.alpha_composer.orchestrator import AlphaOrchestrator
from agents.alpha_composer.scorer import compute_alpha_score, score_to_recommendation, build_summary

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("alpha-composer")

SERVICE_IDS = {
    "whale":     os.environ["WHALE_TRACKER_SERVICE_ID"],
    "health":    os.environ["PROTOCOL_HEALTH_SERVICE_ID"],
    "dd":        os.environ["TOKEN_DD_SERVICE_ID"],
    "sentiment": os.environ["SENTIMENT_FUSION_SERVICE_ID"],
}

async def deliver(client, orchestrator: AlphaOrchestrator, order_id: str, requirements: str):
    try:
        req = AlphaRequest.model_validate_json(requirements)
        whale, health, dd, sentiment = await orchestrator.run(
            req.token_address, req.chain.value, req.token_symbol
        )

        alpha_score, confidence = compute_alpha_score(whale, health, dd, sentiment)
        partial = any(
            isinstance(r, dict) and r.get("status") == "unavailable"
            for r in [whale, health, dd, sentiment]
        )

        resp = AlphaResponse(
            alpha_score=alpha_score,
            recommendation=score_to_recommendation(alpha_score, dd),
            confidence_pct=confidence,
            whale_activity=whale,
            protocol_health=health,
            token_dd=dd,
            sentiment=sentiment,
            summary=build_summary(alpha_score, whale, health, dd, sentiment),
            generated_at=datetime.now(timezone.utc).isoformat(),
            sub_agent_costs_usdc=4.0,
            partial_report=partial,
        )

        await client.deliver_order(order_id, DeliverOrderRequest(
            deliverable_type=DeliverableType.TEXT,
            deliverable_text=resp.model_dump_json(),
        ))
        log.info(f"Delivered alpha report for order {order_id}, score={alpha_score}")
    except Exception as e:
        log.error(f"Failed order {order_id}: {e}")
        await client.reject_order(order_id, str(e))

async def main():
    client = make_client()
    orchestrator = AlphaOrchestrator(client, SERVICE_IDS)
    stream = await client.connect_websocket()

    orchestrator.register_handlers(stream)

    orphaned = await client.list_orders(ListOptions(role="provider", status="paid"))
    for order in (orphaned.orders or []):
        asyncio.create_task(deliver(client, orchestrator, order.id, order.requirements))

    stream.on(EventType.NEGOTIATION_CREATED,
              lambda e: asyncio.create_task(client.accept_negotiation(e.negotiation_id)))
    stream.on(EventType.ORDER_PAID,
              lambda e: asyncio.create_task(deliver(client, orchestrator, e.order_id, e.requirements)))

    log.info("Alpha Composer listening...")
    await stream.listen()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 8: Create `agents/alpha_composer/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY agents/alpha_composer/ ./agents/alpha_composer/
COPY agents/__init__.py ./agents/__init__.py
CMD ["python", "-m", "agents.alpha_composer.main"]
```

- [ ] **Step 9: Run all tests**

```bash
pytest tests/ -v
```

Expected: 32 PASSED (4 + 6 + 6 + 5 + 11).

- [ ] **Step 10: Commit**

```bash
git add .
git commit -m "feat: add alpha-composer orchestrator with A2A coordination"
```

---

## Task 7: Docker Compose + Deployment Config

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

**Interfaces:**
- Consumes: All 5 Dockerfiles from Tasks 2-6
- Produces: Single `docker-compose up -d` command launches all 5 agents

- [ ] **Step 1: Create `.env.example`**

```bash
# CROO Network (same for all agents)
CROO_API_URL=https://api.croo.network
CROO_WS_URL=wss://api.croo.network/ws

# Agent SDK keys — one per agent, from agent.croo.network dashboard
WHALE_SDK_KEY=croo_sk_...
HEALTH_SDK_KEY=croo_sk_...
DD_SDK_KEY=croo_sk_...
SENTIMENT_SDK_KEY=croo_sk_...
ALPHA_SDK_KEY=croo_sk_...

# Sub-agent service IDs — from dashboard after registering each service
WHALE_TRACKER_SERVICE_ID=svc_...
PROTOCOL_HEALTH_SERVICE_ID=svc_...
TOKEN_DD_SERVICE_ID=svc_...
SENTIMENT_FUSION_SERVICE_ID=svc_...

# External data APIs (free — register at etherscan.io and basescan.org)
ETHERSCAN_API_KEY=
BASESCAN_API_KEY=
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
version: "3.9"

x-common: &common
  restart: unless-stopped
  environment:
    CROO_API_URL: ${CROO_API_URL}
    CROO_WS_URL: ${CROO_WS_URL}

services:
  whale-tracker:
    <<: *common
    build:
      context: .
      dockerfile: agents/whale_tracker/Dockerfile
    environment:
      CROO_SDK_KEY: ${WHALE_SDK_KEY}
      ETHERSCAN_API_KEY: ${ETHERSCAN_API_KEY}
      BASESCAN_API_KEY: ${BASESCAN_API_KEY}

  protocol-health:
    <<: *common
    build:
      context: .
      dockerfile: agents/protocol_health/Dockerfile
    environment:
      CROO_SDK_KEY: ${HEALTH_SDK_KEY}

  token-dd:
    <<: *common
    build:
      context: .
      dockerfile: agents/token_dd/Dockerfile
    environment:
      CROO_SDK_KEY: ${DD_SDK_KEY}
      ETHERSCAN_API_KEY: ${ETHERSCAN_API_KEY}
      BASESCAN_API_KEY: ${BASESCAN_API_KEY}

  sentiment-fusion:
    <<: *common
    build:
      context: .
      dockerfile: agents/sentiment_fusion/Dockerfile
    environment:
      CROO_SDK_KEY: ${SENTIMENT_SDK_KEY}

  alpha-composer:
    <<: *common
    build:
      context: .
      dockerfile: agents/alpha_composer/Dockerfile
    environment:
      CROO_SDK_KEY: ${ALPHA_SDK_KEY}
      WHALE_TRACKER_SERVICE_ID: ${WHALE_TRACKER_SERVICE_ID}
      PROTOCOL_HEALTH_SERVICE_ID: ${PROTOCOL_HEALTH_SERVICE_ID}
      TOKEN_DD_SERVICE_ID: ${TOKEN_DD_SERVICE_ID}
      SENTIMENT_FUSION_SERVICE_ID: ${SENTIMENT_FUSION_SERVICE_ID}
```

- [ ] **Step 4: Build all images locally to verify Dockerfiles are correct**

```bash
docker-compose build
```

Expected: 5 images built, no errors.

- [ ] **Step 5: Deploy to Oracle Cloud (free tier) or Hetzner**

Oracle Cloud Always Free gives 2 AMD VM instances with 1GB RAM — sufficient for all 5 containers.

```bash
# On your VPS:
git clone <your-repo> && cd croo-defi-alpha-mesh
cp .env.example .env
# Fill in all values in .env from CROO dashboard and API key registrations
docker-compose up -d
docker-compose logs -f  # Verify all 5 agents show "listening..."
```

Expected logs:
```
whale-tracker_1      | Whale Tracker agent listening...
protocol-health_1    | Protocol Health agent listening...
token-dd_1           | Token DD agent listening...
sentiment-fusion_1   | Sentiment Fusion agent listening...
alpha-composer_1     | Alpha Composer listening...
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: add docker-compose deployment config"
```

---

## Task 8: E2E Smoke Test

**Files:**
- Create: `scripts/test_e2e.py`

**Purpose:** Places one real order to `alpha-composer` via CAP, prints the full JSON response. Run this manually after deployment to confirm the A2A chain works end-to-end. Requires real USDC in the test wallet.

- [ ] **Step 1: Create `scripts/test_e2e.py`**

```python
"""
E2E smoke test — places one real CAP order to alpha-composer and prints result.
Requires: CROO_SDK_KEY set to a FUNDED test wallet (not a agent key — a human wallet SDK key).
Run: python scripts/test_e2e.py
Cost: 5 USDC (paid to alpha-composer, which pays 4 USDC to sub-agents)
"""
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from croo import Config, AgentClient, EventType, NegotiateOrderRequest, ListOptions

ALPHA_SERVICE_ID = os.environ["ALPHA_COMPOSER_SERVICE_ID"]
# Test with WETH on Base as a known token
TEST_TOKEN = "0x4200000000000000000000000000000000000006"
TEST_CHAIN = "base"

async def main():
    config = Config(
        base_url=os.environ["CROO_API_URL"],
        ws_url=os.environ["CROO_WS_URL"],
    )
    client = AgentClient(config, os.environ["TEST_WALLET_SDK_KEY"])
    stream = await client.connect_websocket()

    done = asyncio.Event()
    result = {}

    async def on_created(e):
        print(f"Order created: {e.order_id} — paying...")
        await client.pay_order(e.order_id)

    async def on_completed(e):
        print(f"Order completed: {e.order_id}")
        delivery = await client.get_delivery(e.order_id)
        result["data"] = json.loads(delivery.deliverable_text)
        done.set()

    stream.on(EventType.ORDER_CREATED, on_created)
    stream.on(EventType.ORDER_COMPLETED, on_completed)

    print(f"Placing order to alpha-composer service {ALPHA_SERVICE_ID}...")
    neg = await client.negotiate_order(NegotiateOrderRequest(
        service_id=ALPHA_SERVICE_ID,
        requirements=json.dumps({
            "token_address": TEST_TOKEN,
            "chain": TEST_CHAIN,
            "token_symbol": "WETH",
        }),
    ))
    print(f"Negotiation ID: {neg.negotiation_id} — waiting for provider acceptance...")

    try:
        await asyncio.wait_for(done.wait(), timeout=900)
        print("\n=== ALPHA REPORT ===")
        print(json.dumps(result["data"], indent=2))
    except asyncio.TimeoutError:
        print("ERROR: Order timed out after 15 minutes")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Add `ALPHA_COMPOSER_SERVICE_ID` and `TEST_WALLET_SDK_KEY` to `.env`**

Both come from the CROO dashboard:
- `ALPHA_COMPOSER_SERVICE_ID`: service ID of the alpha-composer service (not agent)
- `TEST_WALLET_SDK_KEY`: SDK key for a separate funded wallet (separate from agent wallets)

- [ ] **Step 3: Run the E2E test (costs 5 USDC)**

```bash
python scripts/test_e2e.py
```

Expected output:
```
Placing order to alpha-composer service svc_...
Negotiation ID: neg_... — waiting for provider acceptance...
Order created: ord_... — paying...
Order completed: ord_...

=== ALPHA REPORT ===
{
  "alpha_score": 65,
  "recommendation": "hold",
  "confidence_pct": 75,
  ...
}
```

If the result shows `partial_report: true` for any sub-agent, check that sub-agent's Docker logs for errors.

- [ ] **Step 4: Final full test suite**

```bash
pytest tests/ -v
```

Expected: 32 PASSED, 0 failed.

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat: add e2e smoke test script"
git tag v1.0.0
```

---

## Post-Build Checklist

After all tasks complete:

- [ ] Register each agent on agent.croo.network dashboard (manual, ~10 min total)
  - For each: set service name, price, SLA, input schema (JSON), output schema (JSON)
  - Note the service IDs and add to `.env`
- [ ] Deposit 8 USDC to alpha-composer AA wallet (dashboard shows the address)
- [ ] Run `scripts/test_e2e.py` to confirm full A2A chain works
- [ ] Claim onboarding bounty at campaigns.croo.network before Jul 9
- [ ] Create 5-min demo video: show a real order flowing through all 5 agents
- [ ] Open GitHub repo as public with MIT license
- [ ] File BUIDL on DoraHacks with dual track: Research & Intelligence + Open A2A
