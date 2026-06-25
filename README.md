# Crook
# DeFi Alpha Mesh

5 agents, each with a wallet. They pay each other.

Point `alpha-composer` at any token address. It splits the work across 4 
specialists, waits for all of them to finish, and returns one report. Every 
handoff is a real USDC order settled on Base through CROO's Agent Protocol.

Built for the CROO Agent Hackathon 2026.

## Agents

| Agent             | Price    | Data                                          |
|-------------------|----------|-----------------------------------------------|
| `whale-tracker`   | 0.5 USDC | Etherscan/Basescan large transfer detection   |
| `protocol-health` | 1 USDC   | DeFi Llama TVL and audit records              |
| `token-dd`        | 2 USDC   | GoPlus Security (honeypot, taxes, ownership)  |
| `sentiment-fusion`| 0.5 USDC | CoinGecko community votes + 24h price trend   |
| `alpha-composer`  | 5 USDC   | Hires all four, returns the combined report   |

One query to `alpha-composer` generates 5 on-chain orders. The sub-agents are 
also listed independently on the CROO Agent Store — other builders can hire 
them directly.

## Stack

Python 3.10+, croo-sdk, pydantic, httpx. All data sources are free tier. Gas 
is covered by CROO.

## Run it

cp .env.example .env   # CROO SDK keys + free Etherscan/Basescan API keys
docker-compose up -d

## License

MIT
