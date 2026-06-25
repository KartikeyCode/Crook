# DeFi Alpha Mesh — Design Spec
**Date:** 2026-06-23  
**Hackathon:** CROO Agent Hackathon (DoraHacks, deadline Jul 12 2026)  
**Prize pool:** $10,200 USDC + $11,220 leaderboard + $50 onboarding bounty  
**Track:** Research & Intelligence Agents + Open A2A Agents (dual track)  
**Stack:** Python 3.10+, croo-sdk, Base mainnet  
**Status:** Approved for implementation

---

## 1. Context & Strategic Position

### Why this exists
CROO Agent Store launched June 2026 with **0 live agents and 0 orders**. First-mover advantage is maximum. Only 4 BUIDLs submitted, 93 hackers registered — most haven't built yet.

### Judging weights
| Criterion | Weight | How we win |
|---|---|---|
| Technical Execution | 30% | Robust CAP integration + 10+ real orders (bonus) |
| A2A Composability | 25% | 5 agents hiring each other = high number/diversity/depth |
| Innovation | 20% | Agents autonomously paying each other on-chain — impossible on normal API marketplace |
| Usability & Adoption | 15% | Other hackathon builders hire our data primitives |
| Presentation | 10% | Demo Day |

### Anti-sybil compliance
- 3+ unique counterparty agents: ✅ (5 agents, each independently callable)
- 5+ unique buyer wallets: Target by inviting other builders to use sub-agents during hackathon
- No self-trade patterns: Alpha Composer is a distinct agent from sub-agents

---

## 2. System Architecture

### Overview
5 independent Python agents, each registered on CROO Agent Store with its own AA wallet and SDK key. Sub-agents are pure providers. Alpha Composer is dual-role: provider to clients, requester to sub-agents.

```
External Agent / Human
        │
        │ 5 USDC (via CAP)
        ▼
┌──────────────────────┐
│   alpha-composer     │  ← keeps 1 USDC profit per query
└──────────┬───────────┘
           │ places 4 concurrent A2A orders
     ┌─────┼──────┬───────────┐
     ▼     ▼      ▼           ▼
  whale  token  protocol  sentiment
tracker   dd    health    fusion
 0.5 USDC 2 USDC 1 USDC   0.5 USDC
     │     │      │           │
     └─────┴──────┴───────────┘
           │ results composed
           ▼
    Final alpha report → client ORDER_COMPLETED
```

**One alpha-composer query = 5 CAP orders total.**  
Two queries = 10+ orders = Technical Execution bonus unlocked.

### Profit model
- Revenue per query: 5 USDC
- Cost per query: 0.5 + 2 + 1 + 0.5 = 4 USDC to sub-agents
- Gas: $0 (CROO-sponsored)
- Margin: **1 USDC per query, infinite scale**

---

## 3. Agent Definitions

### 3.1 whale-tracker
| Field | Value |
|---|---|
| Service name | Whale Tracker |
| Price | 0.50 USDC |
| SLA | 2 minutes |
| Data sources | Etherscan API (free), Basescan API (free) |

**Input schema:**
```json
{
  "token_address": "0x...",
  "chain": "base | ethereum",
  "lookback_hours": 24
}
```

**Output schema:**
```json
{
  "large_movements": [
    {"wallet": "0x...", "amount_usd": 52000, "direction": "buy | sell", "tx_hash": "0x..."}
  ],
  "net_flow": "inflow | outflow | neutral",
  "movement_score": 75,
  "whale_count": 3,
  "data_quality": "full | degraded"
}
```

**Logic:** Query Etherscan/Basescan token transfer events for the contract, filter transfers > $10k USD equivalent, classify direction by wallet type (known exchange vs unknown = whale), compute net flow score.

**Free API calls used:**
- `GET https://api.basescan.org/api?module=account&action=tokentx&contractaddress={addr}&apikey={key}`
- `GET https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={addr}&apikey={key}`

API keys: free to register at etherscan.io and basescan.org.

---

### 3.2 protocol-health
| Field | Value |
|---|---|
| Service name | Protocol Health Monitor |
| Price | 1.00 USDC |
| SLA | 3 minutes |
| Data sources | DeFi Llama API (completely free, no key) |

**Input schema:**
```json
{
  "token_address": "0x...",
  "chain": "base | ethereum"
}
```

**Output schema:**
```json
{
  "protocol_name": "Uniswap",
  "tvl_usd": 1500000,
  "tvl_24h_change_pct": -3.2,
  "tvl_7d_change_pct": 1.8,
  "audit_status": "audited | unaudited | unknown",
  "auditor": "Certik | OpenZeppelin | unknown",
  "chain_count": 4,
  "health_score": 82,
  "data_quality": "full | degraded"
}
```

**Logic:** Call DeFi Llama `/v2/tokens` to resolve address → protocol, then `/protocol/{slug}` for TVL history and metadata. Compute health_score from TVL trend + audit presence.

**Free API calls used:**
- `GET https://api.llama.fi/v2/tokens` (address resolution, no key)
- `GET https://api.llama.fi/protocol/{slug}` (TVL, audits, chains, no key)

---

### 3.3 token-dd
| Field | Value |
|---|---|
| Service name | Token Due Diligence |
| Price | 2.00 USDC |
| SLA | 5 minutes |
| Data sources | GoPlus Security API (free, no key for basic), Basescan API (free) |

**Input schema:**
```json
{
  "token_address": "0x...",
  "chain": "base | ethereum"
}
```

**Output schema:**
```json
{
  "is_honeypot": false,
  "can_sell": true,
  "ownership_renounced": true,
  "contract_verified": true,
  "liquidity_locked": false,
  "buy_tax_pct": 2.0,
  "sell_tax_pct": 2.0,
  "risk_flags": ["high_sell_tax", "proxy_contract"],
  "risk_level": "low | medium | high | critical",
  "dd_score": 78,
  "data_quality": "full | degraded"
}
```

**Logic:** GoPlus `/api/v1/token_security/{chain_id}` returns honeypot status, taxes, ownership. Basescan `/api?module=contract&action=getabi` checks verification. Compute dd_score from weighted risk flags.

**Chain ID mapping:** ethereum=1, base=8453

**Free API calls used:**
- `GET https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={addr}` (no key needed)
- `GET https://api.basescan.org/api?module=contract&action=getsourcecode&address={addr}&apikey={key}`

---

### 3.4 sentiment-fusion
| Field | Value |
|---|---|
| Service name | Sentiment Fusion |
| Price | 0.50 USDC |
| SLA | 2 minutes |
| Data sources | CoinGecko free API (no key, 30 req/min) |

**Input schema:**
```json
{
  "token_address": "0x...",
  "token_symbol": "PEPE",
  "chain": "base | ethereum"
}
```

**Output schema:**
```json
{
  "sentiment": "bullish | bearish | neutral",
  "social_score": 65,
  "sentiment_votes_up_pct": 72.3,
  "sentiment_votes_down_pct": 27.7,
  "price_change_24h_pct": 4.2,
  "volume_spike_24h": false,
  "market_cap_rank": 42,
  "data_quality": "full | degraded"
}
```

**Logic:** Resolve token via CoinGecko `/api/v3/coins/list` (cache this list), fetch `/api/v3/coins/{id}` for sentiment_votes and market data. Classify sentiment from votes + 24h price momentum.

**Free API calls used:**
- `GET https://api.coingecko.com/api/v3/coins/list` (cache, refresh daily)
- `GET https://api.coingecko.com/api/v3/coins/{id}?localization=false&tickers=false&community_data=true`

---

### 3.5 alpha-composer (orchestrator)
| Field | Value |
|---|---|
| Service name | DeFi Alpha Report |
| Price | 5.00 USDC |
| SLA | 15 minutes |
| Data sources | 4 sub-agents via CAP A2A |

**Input schema:**
```json
{
  "token_address": "0x...",
  "chain": "base | ethereum",
  "token_symbol": "optional string"
}
```

**Output schema:**
```json
{
  "alpha_score": 73,
  "recommendation": "accumulate | hold | avoid | watch",
  "confidence_pct": 78,
  "whale_activity": { /* whale-tracker output */ },
  "protocol_health": { /* protocol-health output */ },
  "token_dd": { /* token-dd output */ },
  "sentiment": { /* sentiment-fusion output */ },
  "summary": "On-chain whale inflow detected (+75 score). Protocol TVL stable. No honeypot risk. Sentiment bullish. Recommendation: accumulate with caution.",
  "generated_at": "2026-06-23T10:00:00Z",
  "sub_agent_costs_usdc": 4.0,
  "partial_report": false
}
```

---

## 4. CAP Integration Pattern (Python)

### Provider pattern (all 5 agents)
```python
import asyncio
from croo import Config, AgentClient, EventType, DeliverOrderRequest, DeliverableType

async def run_provider(sdk_key: str, handler):
    config = Config(
        base_url="https://api.croo.network",
        ws_url="wss://api.croo.network/ws"
    )
    client = AgentClient(config, sdk_key)
    stream = await client.connect_websocket()

    async def on_negotiation(e):
        await client.accept_negotiation(e.negotiation_id)

    async def on_paid(e):
        result = await handler(e.order_id, e.requirements)
        await client.deliver_order(e.order_id, DeliverOrderRequest(
            deliverable_type=DeliverableType.TEXT,
            deliverable_text=result,
        ))

    stream.on(EventType.NEGOTIATION_CREATED, on_negotiation)
    stream.on(EventType.ORDER_PAID, on_paid)
    await stream.listen()
```

### Requester pattern (alpha-composer only)
```python
async def hire_sub_agent(client, service_id: str, requirements: dict) -> dict:
    completion = asyncio.Event()
    result = {}

    neg = await client.negotiate_order(NegotiateOrderRequest(
        service_id=service_id,
        requirements=json.dumps(requirements),
    ))

    # Track by order_id set after ORDER_CREATED
    pending[neg.negotiation_id] = (completion, result)

    await asyncio.wait_for(completion.wait(), timeout=600)
    return result["data"]
```

### Alpha Composer coordination (asyncio.gather)
```python
async def compose_report(client, token_address, chain, token_symbol):
    whale, health, dd, sentiment = await asyncio.gather(
        hire_sub_agent(client, WHALE_SERVICE_ID, {"token_address": token_address, "chain": chain, "lookback_hours": 24}),
        hire_sub_agent(client, HEALTH_SERVICE_ID, {"token_address": token_address, "chain": chain}),
        hire_sub_agent(client, DD_SERVICE_ID,     {"token_address": token_address, "chain": chain}),
        hire_sub_agent(client, SENTIMENT_SERVICE_ID, {"token_address": token_address, "chain": chain, "token_symbol": token_symbol or ""}),
        return_exceptions=True  # partial delivery on sub-agent failure
    )
    return build_alpha_report(whale, health, dd, sentiment)
```

---

## 5. Error Handling

| Failure | Detection | Response |
|---|---|---|
| Sub-agent SLA expiry | `ORDER_EXPIRED` event | Mark field `{"status": "unavailable"}`, deliver partial report |
| Alpha Composer low USDC | `is_insufficient_balance(err)` | `reject_order()` to client, client gets full refund |
| WebSocket disconnect | SDK auto-reconnects (1s–30s backoff) | On reconnect: `list_orders(role="provider", status="paid")` → resume |
| External API failure | 3-retry exponential backoff | Deliver with `"data_quality": "degraded"` |
| Sub-agent takes >10min | `asyncio.wait_for` timeout=600s | Treat same as expiry, partial report |

**Startup recovery:** Every process start runs:
```python
orphaned = await client.list_orders(ListOptions(role="provider", status="paid"))
for order in orphaned.orders:
    asyncio.create_task(resume_delivery(order))
```

**Alpha Composer minimum USDC buffer:** 8 USDC in AA wallet at all times (covers 2 concurrent queries). Monitor and alert if below.

---

## 6. Repo Structure

```
croo-defi-alpha-mesh/
├── README.md
├── docker-compose.yml
├── .env.example
├── shared/
│   ├── __init__.py
│   ├── croo_client.py          # AgentClient factory
│   ├── schemas.py              # Pydantic I/O models for all agents
│   └── data_sources/
│       ├── etherscan.py        # Etherscan + Basescan wrappers
│       ├── defillama.py        # DeFi Llama wrapper
│       ├── goplus.py           # GoPlus Security wrapper
│       └── coingecko.py        # CoinGecko wrapper
├── agents/
│   ├── whale_tracker/
│   │   ├── main.py
│   │   ├── fetcher.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── protocol_health/
│   │   ├── main.py
│   │   ├── fetcher.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── token_dd/
│   │   ├── main.py
│   │   ├── fetcher.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── sentiment_fusion/
│   │   ├── main.py
│   │   ├── fetcher.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── alpha_composer/
│       ├── main.py
│       ├── orchestrator.py
│       ├── requirements.txt
│       └── Dockerfile
└── scripts/
    └── test_e2e.py             # Place real order to alpha-composer, verify output
```

---

## 7. Deployment

### Infrastructure: Oracle Cloud Always Free (zero cost)
- 2 AMD Compute instances, 1GB RAM each — free forever
- Container 1: whale_tracker + protocol_health + sentiment_fusion
- Container 2: token_dd + alpha_composer
- `docker-compose up -d` on each

**Alternative:** Hetzner CX11 (~€4/month) if Oracle free tier has quota issues.

### Environment variables per agent
```bash
# All agents
CROO_API_URL=https://api.croo.network
CROO_WS_URL=wss://api.croo.network/ws
CROO_SDK_KEY=croo_sk_<agent-specific>

# whale_tracker + token_dd
ETHERSCAN_API_KEY=<free from etherscan.io>
BASESCAN_API_KEY=<free from basescan.org>

# alpha_composer only (sub-agent service IDs from dashboard)
WHALE_TRACKER_SERVICE_ID=<from CROO dashboard>
PROTOCOL_HEALTH_SERVICE_ID=<from CROO dashboard>
TOKEN_DD_SERVICE_ID=<from CROO dashboard>
SENTIMENT_FUSION_SERVICE_ID=<from CROO dashboard>
```

### One-time wallet funding
```
alpha-composer AA wallet: deposit 8 USDC (covers 2 concurrent queries as float)
Sub-agent wallets: $0 — earn on first order
```

---

## 8. Free External APIs Summary

| API | Key required | Rate limit | Cost |
|---|---|---|---|
| DeFi Llama | No | Generous | $0 |
| GoPlus Security | No | Reasonable | $0 |
| CoinGecko | No (free tier) | 30 req/min | $0 |
| Etherscan | Yes (free signup) | 5 req/s | $0 |
| Basescan | Yes (free signup) | 5 req/s | $0 |
| CROO gas fees | N/A | N/A | $0 (sponsored) |
| **Total infra cost** | | | **$0–4/month** |

---

## 9. Timeline (19 days to Jul 12 deadline)

| Days | Dates | Milestone |
|---|---|---|
| 1–2 | Jun 23–24 | CROO account, register 5 agents on dashboard, scaffold repo, get all API keys |
| 3–6 | Jun 25–28 | Build 4 sub-agents (parallelizable, ~150 lines each) |
| 7–9 | Jun 29–Jul 1 | Build alpha-composer orchestrator |
| 10–11 | Jul 2–3 | Deploy to Oracle/Hetzner, fund alpha-composer with 8 USDC, smoke test |
| 12–13 | Jul 4–5 | **Claim onboarding bounty** ($10 × 5 agents = $50, deadline Jul 9) |
| 14–16 | Jul 6–8 | Invite other hackathon builders to use sub-agents → diverse buyer wallets |
| 17–19 | Jul 9–12 | Demo video (max 5 min), README polish, DoraHacks BUIDL submission |

**Hard dependency:** Onboarding bounty deadline Jul 9 — agents must be live and have settled real orders by Jul 8.

---

## 10. Submission Checklist

- [ ] 5 agents listed on CROO Agent Store
- [ ] All 5 integrated with CAP (callable, USDC-settling)
- [ ] 10+ real CAP orders during hackathon period (Technical Execution bonus)
- [ ] 3+ unique counterparty agents (A2A requirement)
- [ ] 5+ unique buyer wallets (anti-sybil)
- [ ] Public GitHub repo (MIT license)
- [ ] Max 5-min demo video
- [ ] BUIDL filed on DoraHacks with all required fields
- [ ] Dual track selected: Research & Intelligence + Open A2A

---

## 11. Competitive Moat

**Why this can't be replicated on a normal API marketplace:**
Agents autonomously hold wallets, negotiate prices, place orders, and receive payment without any human intermediary. The sub-agents earn USDC directly into their own on-chain identities. This economic mesh — where data primitives get paid by orchestrators that get paid by clients, all settled on Base with no platform taking a cut — is only possible on CAP.

**Why individual sub-agents are strategically important:**
Other hackathon participants who need DeFi data will find `whale-tracker` (0.50 USDC) and `token-dd` (2 USDC) on the Agent Store and hire them directly. This generates diverse orders and buyer wallets we didn't initiate — passive order accumulation from competitors.
