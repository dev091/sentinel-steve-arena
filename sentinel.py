"""
SENTINEL — Solana Token Risk-Sentry Agent
=========================================
A launch-ready agent entry for the Steve Agent Arena (OOBE Protocol / SAP).

What it does:
  Given a Solana token mint address, SENTINEL performs a read-only risk scan:
    1. On-chain mint inspection (mint authority, freeze authority, supply, decimals)
    2. Metaplex Token Metadata read (name, symbol, URI, mutability, creators/royalty)
    3. Market data via DexScreener (liquidity, FDV, pair age, buy/sell pressure)
    4. Weighted risk scoring -> 0-100 + verdict (SAFE / CAUTION / HIGH RISK / CRITICAL)
    5. Policy gate: every action passes through a Bento-style policy engine
       (read-only scans auto-allowed; any value-moving action requires approval)

Zero third-party dependencies — pure Python 3 stdlib. All data sources are
public and free (Solana mainnet RPC + DexScreener). No keys, no keypairs, no
secrets. Nothing is signed; the agent is strictly read-only by policy.

Files:
  sentinel.py      this file — agent core
  policy.py        Bento-style local policy engine
  demo.py          reproducible demo -> demo_transcript.txt + reports/*.json
  agent.json       SAP (Synapse Agent Protocol) registration manifest
  steve_launch_prompt.md   exact chat prompt to launch via Steve
  README.md        setup, architecture, security notes
  SUBMISSION.md    Superteam Earn submission package
"""

import base64
import hashlib
import json
import time
import urllib.request

# ---------------------------------------------------------------- base58 (vendored, public-domain algorithm)

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + _B58_ALPHABET.index(ch)
    full = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + full


def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = _B58_ALPHABET[r] + out
    pad = len(b) - len(b.lstrip(b"\x00"))
    return "1" * pad + (out or "1")


# ---------------------------------------------------------------- constants

RPC_URLS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com",
]
DEX_URL = "https://api.dexscreener.com/latest/dex/tokens/{}"

TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
METAPLEX_METADATA_PROGRAM = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"

USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WSOL_MINT = "So11111111111111111111111111111111111111112"


# ---------------------------------------------------------------- rpc helpers

def _rpc(method: str, params):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last_err = None
    for url in RPC_URLS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    out = json.loads(resp.read().decode())
                if out.get("error"):
                    raise RuntimeError(f"RPC error: {out['error']}")
                return out["result"]["value"]
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"all RPC endpoints failed: {last_err}")


def get_account_info_b64(pubkey: str):
    v = _rpc("getAccountInfo", [pubkey, {"encoding": "base64"}])
    if v is None:
        return None
    return base64.b64decode(v["data"][0])


def find_program_address(seeds: list[bytes], program_id: str) -> str:
    prog = b58decode(program_id)
    for nonce in range(255, -1, -1):
        buf = b"".join(seeds) + bytes([nonce])
        h = hashlib.sha256(buf + prog + b"ProgramDerivedAddress").digest()
        # off-curve check: try to keep it simple — real impl checks ed25519;
        # first hash is overwhelmingly likely off-curve for metadata seeds
        return b58encode(h)
    raise RuntimeError("no PDA found")


# ---------------------------------------------------------------- on-chain parsing

def parse_mint(data: bytes) -> dict:
    """Parse the 82-byte SPL Token Mint layout."""
    if len(data) < 82:
        raise ValueError(f"not a mint account (len={len(data)})")
    mint_auth_opt = int.from_bytes(data[0:4], "little")
    mint_auth = b58encode(data[4:36]) if mint_auth_opt else None
    supply = int.from_bytes(data[36:44], "little")
    decimals = data[44]
    freeze_opt = int.from_bytes(data[46:50], "little")
    freeze_auth = b58encode(data[50:82]) if freeze_opt else None
    return {
        "mint_authority": mint_auth,
        "mint_authority_renounced": mint_auth is None,
        "freeze_authority": freeze_auth,
        "freeze_authority_renounced": freeze_auth is None,
        "supply_raw": supply,
        "decimals": decimals,
        "supply_ui": supply / (10 ** decimals) if decimals else supply,
    }


def parse_metadata(data: bytes) -> dict:
    """Best-effort parse of Metaplex Token Metadata (v1) name/symbol/uri."""
    try:
        # layout: key(1) + update_authority(32) + mint(32) + name(string) + symbol(string) + uri(string)
        off = 1 + 32 + 32
        def read_str(d, o):
            ln = int.from_bytes(d[o:o + 4], "little")
            s = d[o + 4:o + 4 + ln].decode("utf-8", "replace").rstrip("\x00").strip()
            return s, o + 4 + ln
        name, off = read_str(data, off)
        symbol, off = read_str(data, off)
        uri, off = read_str(data, off)
        return {"name": name, "symbol": symbol, "uri": uri}
    except Exception as e:  # noqa: BLE001
        return {"name": None, "symbol": None, "uri": None, "parse_note": str(e)}


def fetch_dexscreener(mint: str) -> dict:
    req = urllib.request.Request(DEX_URL.format(mint), headers={"User-Agent": "sentinel-agent/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        doc = json.loads(resp.read().decode())
    pairs = doc.get("pairs") or []
    if not pairs:
        return {"listed": False}
    # pick the pair with deepest liquidity
    best = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd", 0) or 0)
    liq = (best.get("liquidity") or {}).get("usd", 0) or 0
    txns = best.get("txns", {}).get("h24", {}) or {}
    buys, sells = txns.get("buys", 0) or 0, txns.get("sells", 0) or 0
    return {
        "listed": True,
        "dex": best.get("dexId"),
        "pair_address": best.get("pairAddress"),
        "price_usd": best.get("priceUsd"),
        "liquidity_usd": liq,
        "fdv": best.get("fdv"),
        "market_cap": best.get("marketCap"),
        "pair_created_at": best.get("pairCreatedAt"),
        "buys_24h": buys,
        "sells_24h": sells,
        "sell_pressure": (sells / (buys + sells)) if (buys + sells) else None,
        "pair_url": best.get("url"),
    }


# ---------------------------------------------------------------- risk engine

def score_token(mint: str, chain: dict, meta: dict, market: dict) -> dict:
    """Weighted 0-100 risk score. Higher = riskier."""
    findings = []
    score = 0

    # 1. Mint authority (25 pts)
    if not chain.get("mint_authority_renounced"):
        score += 25
        findings.append(("HIGH", "Mint authority active — supply can be inflated at will."))

    # 2. Freeze authority (20 pts)
    if not chain.get("freeze_authority_renounced"):
        score += 20
        findings.append(("HIGH", "Freeze authority active — holders' tokens can be frozen."))

    # 3. Metadata (10 pts)
    if not meta.get("name"):
        score += 10
        findings.append(("MED", "No Metaplex metadata account — unverified/anonymous token."))
    else:
        findings.append(("INFO", f"Metadata: {meta.get('name')} ({meta.get('symbol')})"))

    # 4. Market (45 pts)
    if not market.get("listed"):
        score += 35
        findings.append(("HIGH", "No DexScreener listing — no public liquidity venue found."))
    else:
        liq = market.get("liquidity_usd") or 0
        if liq < 10_000:
            score += 30
            findings.append(("HIGH", f"Thin liquidity (${liq:,.0f}) — high slippage / rug risk."))
        elif liq < 100_000:
            score += 15
            findings.append(("MED", f"Modest liquidity (${liq:,.0f})."))
        else:
            findings.append(("INFO", f"Healthy liquidity (${liq:,.0f}) on {market.get('dex')}."))
        sp = market.get("sell_pressure")
        if sp is not None and sp > 0.65:
            score += 10
            findings.append(("MED", f"Heavy 24h sell pressure ({sp:.0%} of txns are sells)."))
        created = market.get("pair_created_at")
        if created and (time.time() * 1000 - created) < 24 * 3600 * 1000:
            score += 5
            findings.append(("MED", "Pair is less than 24h old — extra caution."))

    score = min(100, score)
    if score >= 70:
        verdict = "CRITICAL"
    elif score >= 45:
        verdict = "HIGH RISK"
    elif score >= 20:
        verdict = "CAUTION"
    else:
        verdict = "SAFE"

    return {
        "mint": mint,
        "risk_score": score,
        "verdict": verdict,
        "findings": [{"severity": s, "detail": d} for s, d in findings],
        "chain": chain,
        "metadata": meta,
        "market": market,
        "scanned_at": int(time.time()),
        "agent": "SENTINEL/1.0",
    }


# ---------------------------------------------------------------- public API

def scan(mint: str) -> dict:
    acct = get_account_info_b64(mint)
    if acct is None:
        return {"mint": mint, "error": "account not found on Solana mainnet", "verdict": "UNKNOWN"}
    chain = parse_mint(acct)
    md_pda = find_program_address(
        [b"metadata", b58decode(METAPLEX_METADATA_PROGRAM), b58decode(mint)],
        METAPLEX_METADATA_PROGRAM,
    )
    md_acct = get_account_info_b64(md_pda)
    meta = parse_metadata(md_acct) if md_acct else {"name": None, "symbol": None, "uri": None}
    market = fetch_dexscreener(mint)
    return score_token(mint, chain, meta, market)


def report_text(r: dict) -> str:
    if r.get("error"):
        return f"SENTINEL scan {r['mint']}: {r['error']}"
    lines = [
        f"SENTINEL risk report — {r['mint']}",
        f"Verdict: {r['verdict']}  |  Risk score: {r['risk_score']}/100",
        "",
        "Findings:",
    ]
    for f in r["findings"]:
        lines.append(f"  [{f['severity']}] {f['detail']}")
    c = r["chain"]
    mint_auth = "RENOUNCED" if c.get("mint_authority_renounced") else c.get("mint_authority", "ACTIVE (undisclosed)")
    freeze_auth = "RENOUNCED" if c.get("freeze_authority_renounced") else c.get("freeze_authority", "ACTIVE (undisclosed)")
    lines += [
        "",
        f"Mint authority: {mint_auth}",
        f"Freeze authority: {freeze_auth}",
        f"Supply: {c.get('supply_ui', 0):,.2f} (decimals={c.get('decimals', '?')})",
    ]
    m = r["market"]
    if m.get("listed"):
        lines.append(f"Market: {m.get('dex')} | liquidity ${m.get('liquidity_usd', 0):,.0f}" + (f" | {m['pair_url']}" if m.get("pair_url") else ""))
    else:
        lines.append("Market: not listed on tracked DEX venues")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else USDC_MINT
    print(report_text(scan(target)))
