# SENTINEL — Solana Token Risk-Sentry Agent

**Steve Agent Arena entry · OOBE Protocol · Superteam Earn bounty**

SENTINEL is a read-only Solana token risk scanner built to be launched as an
agent in Steve's arena. Give it any SPL mint — it inspects on-chain
authorities, Metaplex metadata, and live DEX liquidity, then returns a 0–100
risk score with a plain-English verdict. It never signs, never moves funds:
a Bento-style policy engine blocks all value-moving actions by default.

## Quickstart (zero dependencies, Python 3.8+)

```bash
python3 demo.py            # full reproducible demo -> demo_transcript.txt + reports/*.json
python3 sentinel.py <MINT> # scan a single mint, e.g.
python3 sentinel.py EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v   # USDC
python3 policy.py          # policy engine: one ALLOW + one DENY demonstration
```

Live demo results (2026-09-16, mainnet):
- **wSOL** → SAFE, 0/100 (authorities renounced, $32M liquidity)
- **USDC** → HIGH RISK, 45/100 — the engine correctly flags USDC's *by-design*
  active mint/freeze authorities (Circle). Authority flags are facts, not
  accusations: regulated stablecoins score here by construction.

## Architecture

```
                        +-------------------+
                        |    Steve chat     |  <- launch: user pastes steve_launch_prompt.md
                        | steve.oobeprotocol.ai
                        +---------+---------+
                                  | sap_build_agent_register_transaction (hosted builder)
                                  v
+----------+    policy gate    +-----------+    public reads    +------------------+
|  caller  | --->  policy.py   ---> sentinel.py  -------------> | Solana mainnet   |
| (Steve / |  ALLOW read-only |  scan()      |                 | RPC (authorities,|
|  user)   |  DENY value-move |  score_token |                 |  Metaplex PDA)   |
+----------+                  +-----+-----+                    +------------------+
                                    |                          +------------------+
                                    v                          | DexScreener API  |
                              JSON report                      | (liquidity, FDV, |
                              + audit log                      |  buy/sell flow)  |
                                                               +------------------+
```

## SAP MCP tools & flows used

Intended on-chain registration (via Steve's hosted builder at launch):
- `sap_build_agent_register_transaction` — builds the unsigned SAP
  `register_agent` tx from `agent.json` (name, description, capabilities)
- SAP registry `register_agent` — on-chain identity (capabilities are
  colon-namespaced, ≤10 caps / ≤5 protocols per the on-chain validator)
- SAP discovery — agent becomes discoverable in the arena

Local agent stack (this repo):
- `sentinel.py` — mint parse, Metaplex metadata PDA + parse, DexScreener,
  weighted risk engine
- `policy.py` — Bento-style policy engine: explicit rules, allow/deny
  decisions, JSON audit log

## Partner technologies

| Partner | Usage |
|---|---|
| OOBE / Synapse / SAP | `agent.json` SAP registration manifest; launch via Steve's hosted builder; arena discovery |
| Bento (pattern) | `policy.py` implements the Bento Guard contract from bounty spec §10.2: policy layer before sensitive actions, one allowed + one blocked action demo, audit log |
| Metaplex | Real on-chain reads of Metaplex Token Metadata accounts (PDA derived, name/symbol/URI parsed) |
| SNS | Planned `.sol` identity link at launch (see `steve_launch_prompt.md`) |
| Solana | mainnet-beta RPC reads (mint authorities, supply); DexScreener market data |

## Security notes

- **Read-only by construction.** No keypair exists anywhere in this repo; no
  signing code paths; nothing is ever submitted to the network.
- **Deny-by-default policy.** `policy.py` blocks `value-moving` and `sign`
  actions; only `read.*` actions are allowed. Every decision is audit-logged.
- **No secrets.** No API keys, no private RPC endpoints, no keypair bytes in
  code, logs, or docs. All data sources are public and free.
- **Honest evidence.** The risky-token case is a *labeled simulated fixture*,
  not a real token — the demo never defames a real project.

## Reproducible commands

```bash
git clone <repo-url> && cd steve-arena
python3 demo.py     # ~10s, writes demo_transcript.txt + reports/
```

## Files

| File | Purpose |
|---|---|
| `sentinel.py` | Agent core (stdlib only) |
| `policy.py` | Bento-style policy engine |
| `demo.py` | Reproducible demo |
| `agent.json` | SAP registration manifest for Steve |
| `steve_launch_prompt.md` | Exact chat prompt to launch via Steve |
| `SUBMISSION.md` | Superteam Earn submission package |
| `demo_transcript.txt` | Demo evidence (generated) |
| `reports/` | JSON reports + policy audit (generated) |
