"""
Reproducible demo for the Steve Agent Arena submission.

Runs:
  1. LIVE scans of real mainnet tokens (wSOL, USDC, USDT, JUP) — real Solana
     mainnet RPC + DexScreener, with per-stage latency benchmark
  2. Malicious-pattern scan: SIMULATED on-chain/market inputs fed through the
     REAL scoring engine (proves the engine fires; inputs are labeled, not a
     real token — the demo never defames a real project)
  3. Comparison table across all scanned tokens
  4. Policy engine: one ALLOWED action + one BLOCKED action (bounty spec 10.2)

Outputs:
  demo_transcript.txt   full console transcript (evidence for judges)
  reports/*.json        machine-readable reports

Usage:  python3 demo.py
"""

import io
import json
import os
import sys
import time
from contextlib import redirect_stdout

import sentinel
import policy

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(HERE, "reports")
os.makedirs(REPORTS, exist_ok=True)

# Extra live-scan targets (real mainnet mints, well-known tokens).
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
JUP_MINT = "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"

# Simulated malicious-pattern INPUTS (labeled fixture, NOT a real token).
# These go through the REAL score_token() engine — nothing is hardcoded.
RISKY_CHAIN = {
    "mint_authority": "SIMULATED-ACTIVE-MINT-AUTHORITY",
    "mint_authority_renounced": False,
    "freeze_authority": "SIMULATED-ACTIVE-FREEZE-AUTHORITY",
    "freeze_authority_renounced": False,
    "supply_raw": 1_000_000_000_000000,
    "decimals": 6,
    "supply_ui": 1_000_000_000,
}
RISKY_META = {"name": None, "symbol": None, "uri": None}
RISKY_MARKET = {
    "listed": True,
    "dex": "raydium",
    "pair_address": "SIMULATED-PAIR",
    "price_usd": "0.0000012",
    "liquidity_usd": 3200,
    "fdv": 1_200_000,
    "market_cap": 1_200_000,
    "pair_created_at": int(time.time() * 1000) - 6 * 3600 * 1000,  # 6h old
    "buys_24h": 18,
    "sells_24h": 82,
    "sell_pressure": 0.82,
    "pair_url": None,
}


def run_live(mint: str, label: str):
    print(f"\n{'='*70}\n[1] LIVE SCAN — {label} ({mint})\n{'='*70}")
    print("  policy check: token.scan ...", end=" ")
    d = policy.evaluate("token.scan", "read")
    print(f"{d['effect'].upper()} (rule={d['rule']})")
    try:
        r, timings = sentinel.scan_timed(mint)
    except Exception as e:  # noqa: BLE001
        print(f"  scan failed (network?): {e}")
        return None, None
    print(sentinel.report_text(r))
    print(f"\n  latency: total {timings['total']:.2f}s "
          f"(rpc_mint {timings['rpc_mint']:.2f}s | rpc_metadata {timings['rpc_metadata']:.2f}s | "
          f"dexscreener {timings['dexscreener']:.2f}s | scoring {timings['scoring']*1000:.1f}ms)")
    path = os.path.join(REPORTS, f"{label.lower().replace(' ', '_')}.json")
    with open(path, "w") as f:
        json.dump(r, f, indent=2)
    print(f"  -> report saved: reports/{os.path.basename(path)}")
    return r, timings


def main():
    buf = io.StringIO()
    with redirect_stdout(buf):
        print("SENTINEL — Steve Agent Arena demo")
        print(f"run at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
        print("data: Solana mainnet-beta RPC (public) + DexScreener (public). Read-only. No keys.")

        results = []
        for mint, label in [(sentinel.WSOL_MINT, "wSOL"),
                            (sentinel.USDC_MINT, "USDC"),
                            (USDT_MINT, "USDT"),
                            (JUP_MINT, "JUP")]:
            r, t = run_live(mint, label)
            if r:
                results.append((label, r, t))

        print(f"\n{'='*70}\n[2] MALICIOUS-PATTERN SCAN — simulated inputs, REAL scoring engine\n"
              f"    (labeled fixture, NOT a real token — no real project is defamed)\n{'='*70}")
        fr = sentinel.score_token("SIMULATED-RISKY-FIXTURE-11111111111111111111",
                                  RISKY_CHAIN, RISKY_META, RISKY_MARKET)
        fr["note"] = ("SIMULATED on-chain/market inputs run through the real score_token() engine. "
                      "Not a real token.")
        print(sentinel.report_text(fr))
        with open(os.path.join(REPORTS, "risky_fixture.json"), "w") as f:
            json.dump(fr, f, indent=2)
        print("\n  -> report saved: reports/risky_fixture.json")

        print(f"\n{'='*70}\n[3] COMPARISON TABLE — live mainnet scans\n{'='*70}")
        print(f"  {'token':<6}{'verdict':<12}{'score':<8}{'liquidity':<16}{'scan time'}")
        for label, r, t in results:
            liq = (r.get("market") or {}).get("liquidity_usd") or 0
            print(f"  {label:<6}{r['verdict']:<12}{r['risk_score']}/100   "
                  f"${liq:>12,.0f}   {t['total']:.1f}s")

        print(f"\n{'='*70}\n[4] POLICY ENGINE — allow + block demonstration\n{'='*70}")
        ok = policy.evaluate("token.scan", "read")
        print(f"  token.scan        -> {ok['effect'].upper()}  (rule={ok['rule']})")
        print(f"    reason: {ok['reason']}")
        blocked = policy.evaluate("swap.execute", "value-moving", {"amount_usd": 500})
        print(f"  swap.execute      -> {blocked['effect'].upper()}  (rule={blocked['rule']})")
        print(f"    reason: {blocked['reason']}")
        with open(os.path.join(REPORTS, "policy_audit.json"), "w") as f:
            f.write(policy.audit_json())
        print("\n  -> audit log saved: reports/policy_audit.json")

        print(f"\n{'='*70}\nDemo complete. SENTINEL is read-only by policy: it scans, scores,\n"
              "and reports — it never signs and never moves funds.\n"
              "Zero dependencies (Python 3 stdlib only). Fully reproducible.\n"
              f"{'='*70}")

    transcript = buf.getvalue()
    with open(os.path.join(HERE, "demo_transcript.txt"), "w") as f:
        f.write(transcript)
    print(transcript)
    print(f"[demo] transcript written to {os.path.join(HERE, 'demo_transcript.txt')}")


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main()
