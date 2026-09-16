# Launch prompt for Steve (steve.oobeprotocol.ai)

Paste this into Steve's chat (with your wallet connected). Steve's hosted
builder will draft the SAP `register_agent` transaction for you to sign —
your private key never leaves your wallet.

---

I want to launch an agent in the arena. Build the registration transaction
with these exact parameters:

**Name:** SENTINEL

**Description:** Solana token risk-sentry: read-only rug-risk scanner. Given
any SPL mint, SENTINEL inspects on-chain authorities (mint/freeze), Metaplex
metadata, and live DEX liquidity, then returns a 0-100 risk score with a
plain-English verdict. Strictly read-only — it never signs, never moves
funds; a Bento-style policy engine blocks all value-moving actions by
default.

**Capabilities** (colon-namespaced, 3 total):
1. `synapse-agent-protocol:token-scan` v1.0.0 — Risk scan of an SPL token
   mint (authorities, metadata, liquidity)
2. `synapse-agent-protocol:market-read` v1.0.0 — Read-only DEX market data
   (liquidity, FDV, buy/sell pressure)
3. `synapse-agent-protocol:risk-report` v1.0.0 — Publish machine-readable
   JSON risk report

**Protocols:** ["synapse-agent-protocol"]
**Pricing:** [] (free reads)

After the registration transaction is ready, please also:
1. Link an SNS `.sol` name for the agent if available (e.g. sentinelarena.sol).
2. Confirm the agent appears in arena discovery.

The full agent spec, working code, demo transcript, and JSON evidence are in
agent.json / sentinel.py / demo_transcript.txt in the linked repo.

---

After signing: save the registration **transaction signature** and the
agent's **public key / PDA** — they go into the Superteam Earn submission
as proof of launch.
