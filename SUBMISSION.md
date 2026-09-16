# SUBMISSION PACKAGE — Steve Agent Arena: Launch Your Agent & Win 500 USDC

Bounty: https://earn.superteam.fun/listing/steve-agent-arena-launch-your-agent-and-win-500-usdc
Sponsor: OOBE Protocol · Prize: 500 USDC (250/150/100) · Deadline: 2026-09-20
Status of this package: **launch-ready — 2 handoff steps remain** (see below).

## Submission title

SENTINEL — Solana Token Risk-Sentry Agent for the Steve Arena

## Submission description (paste into Superteam Earn)

SENTINEL is a read-only Solana token risk scanner built for the Steve Agent
Arena. Give it any SPL mint and it returns a 0–100 rug-risk score with a
plain-English verdict, from three independent signals: (1) on-chain mint &
freeze authorities via Solana mainnet RPC, (2) Metaplex Token Metadata
(name/symbol/URI), (3) live DEX liquidity, FDV and buy/sell pressure via
DexScreener. A Bento-style policy engine gates every action — read-only scans
are auto-allowed, all value-moving actions are denied by default with a full
audit log. The agent never signs and never moves funds.

Live demo evidence (2026-09-16, mainnet, reproducible with `python3 demo.py`):
- wSOL → SAFE, 0/100 (authorities renounced, $32M liquidity)
- USDC → 45/100, correctly flagging Circle's by-design active authorities
- Malicious-pattern fixture → CRITICAL, 95/100
- Policy engine: token.scan ALLOWED, swap.execute DENIED (audit-logged)

SAP registration: agent.json manifest (colon-namespaced capabilities,
3 caps / 1 protocol, within on-chain validator limits), launched via Steve's
hosted builder (`sap_build_agent_register_transaction`).
Registration tx: <PASTE_TX_SIGNATURE_AFTER_LAUNCH>
Agent public key: <PASTE_AFTER_LAUNCH>

Repo: <PASTE_PUBLIC_REPO_URL>
Demo transcript: demo_transcript.txt · Reports: reports/*.json

## Links to include

- Public repo: <push this folder to a public GitHub repo, paste URL>
- Listing: https://earn.superteam.fun/listing/steve-agent-arena-launch-your-agent-and-win-500-usdc
- Steve: https://steve.oobeprotocol.ai/
- Bounty tech spec (judging criteria): https://github.com/oobe-protocol/sap-mcp/blob/main/docs/13_BOUNTY_PROGRAM_TECHNICAL_SPEC.md

## Bounty-spec deliverables checklist (§11)

1. [ ] Public repository — push `steve-arena/` to public GitHub (commands below)
2. [ ] Demo video <5 min — screen-record `python3 demo.py` (~10s runtime);
       transcript already in demo_transcript.txt
3. [x] README with setup instructions — README.md
4. [x] List of SAP MCP tools — README.md (SAP MCP tools & flows)
5. [x] List of partner technologies — README.md (OOBE/SAP, Bento-pattern, Metaplex, SNS, Solana)
6. [x] Architecture — README.md (ASCII diagram)
7. [x] Security notes — README.md (read-only, no keys, deny-by-default)
8. [x] Reproducible commands — README.md (`python3 demo.py`)
9. [~] Evidence of real execution — reports/*.json + demo_transcript.txt (local);
       on-chain registration tx signature after Steve launch

## HANDOFF — exact steps remaining (parent agent / RAHUL)

### Step 1 — Push repo public (2 min)
```bash
cd ~/workspace/crypto/steve-arena
# new public repo, e.g. github.com/<user>/sentinel-arena
git init && git add . && git commit -m "SENTINEL: Steve Agent Arena entry"
gh repo create sentinel-arena --public --source=. --push
# then paste the repo URL into this file's placeholders
```

### Step 2 — Launch the agent via Steve (5 min, needs RAHUL's wallet in browser)
1. Open https://steve.oobeprotocol.ai/ and connect RAHUL's Solana wallet.
2. Paste the full prompt from `steve_launch_prompt.md` into Steve's chat.
3. Steve builds the unsigned `register_agent` tx → review → sign in wallet.
   (Private key never leaves the wallet; Steve's wallet policy requires
   explicit approval for writes.)
4. Save the tx signature + agent public key; paste into the submission
   description above. Optionally link an SNS name if Steve offers it.

### Step 3 — Record demo video (5 min)
Screen-record a terminal running `python3 demo.py` (runtime ~10s, well under
the 5-min limit). Upload unlisted to YouTube / X and link it in the
submission. The transcript (demo_transcript.txt) already documents every
frame.

### Step 4 — Submit on Superteam Earn (needs human signup — the known blocker)
1. RAHUL signs up at https://earn.superteam.fun (human account, no way to
   automate — this is the known blocker).
2. Open the listing, click Submit, paste title + description + links above,
   attach demo video link.
3. Done before 2026-09-20. Winners announced ~2026-09-27.

## Why this can win

- Judging is 25% real SAP MCP usage + 20% partner composition + 20% technical
  correctness: SENTINEL uses real on-chain reads (RPC, Metaplex metadata PDA),
  real market data, a real policy engine implementing the Bento §10.2
  contract, and a SAP-valid registration manifest — no mocks in the live path.
- Product usefulness (15%): rug-risk scanning is a genuine pre-trade workflow
  for Steve's trading-focused audience.
- Only 26 submissions so far; most arena entries are thin chat wrappers. A
  working, reproducible, evidence-backed agent stands out.
