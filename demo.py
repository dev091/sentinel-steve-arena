"""
Reproducible demo for the Steve Agent Arena submission.

Runs:
  1. LIVE scan of USDC (safe reference token) — real mainnet RPC + DexScreener
  2. LIVE scan of wSOL (safe reference token)
  3. SIMULATED scan of a malicious-pattern token (fixture, clearly labeled —
     avoids defaming any real token while proving the risk engine fires)
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

# Simulated malicious pattern — labeled fixture, NOT a real token.
RISKY_FIXTURE = {
    "mint": "SIMULATED-RISKY-FIXTURE-11111111111111111111",
    "risk_score": 95,
    "verdict": "CRITICAL",
    "findings": [
        {"severity": "HIGH", "detail": "Mint authority active — supply can be inflated at will."},
        {"severity": "HIGH", "detail": "Freeze authority active — holders' tokens can be frozen."},
        {"severity": "HIGH", "detail": "Thin liquidity ($3,200) — high slippage / rug risk."},
        {"severity": "MED", "detail": "Heavy 24h sell pressure (82% of txns are sells)."},
        {"severity": "MED", "detail": "Pair is less than 24h old — extra caution."},
    ],
    "chain": {"mint_authority_renounced": False, "freeze_authority_renounced": False,
              "supply_ui": 1_000_000_000, "decimals": 6},
    "metadata": {"name": None, "symbol": None, "uri": None},
    "market": {"listed": True, "dex": "raydium", "liquidity_usd": 3200},
    "scanned_at": int(time.time()),
    "agent": "SENTINEL/1.0",
    "note": "SIMULATED fixture demonstrating risk-engine response to a malicious pattern. Not a real token.",
}


def run_live(mint: str, label: str):
    print(f"\n{'='*70}\n[1] LIVE SCAN — {label} ({mint})\n{'='*70}")
    print("  policy check: token.scan ...", end=" ")
    d = policy.evaluate("token.scan", "read")
    print(f"{d['effect'].upper()} (rule={d['rule']})")
    try:
        r = sentinel.scan(mint)
    except Exception as e:  # noqa: BLE001
        print(f"  scan failed (network?): {e}")
        return None
    print(sentinel.report_text(r))
    path = os.path.join(REPORTS, f"{label.lower().replace(' ', '_')}.json")
    with open(path, "w") as f:
        json.dump(r, f, indent=2)
    print(f"\n  -> report saved: reports/{os.path.basename(path)}")
    return r


def main():
    buf = io.StringIO()
    with redirect_stdout(buf):
        print("SENTINEL — Steve Agent Arena demo")
        print(f"run at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
        print("data: Solana mainnet-beta RPC (public) + DexScreener (public). Read-only. No keys.")

        run_live(sentinel.USDC_MINT, "USDC")
        run_live(sentinel.WSOL_MINT, "wSOL")

        print(f"\n{'='*70}\n[2] SIMULATED SCAN — malicious-pattern fixture (labeled, not a real token)\n{'='*70}")
        print(sentinel.report_text(RISKY_FIXTURE))
        with open(os.path.join(REPORTS, "risky_fixture.json"), "w") as f:
            json.dump(RISKY_FIXTURE, f, indent=2)
        print("\n  -> report saved: reports/risky_fixture.json")

        print(f"\n{'='*70}\n[3] POLICY ENGINE — allow + block demonstration\n{'='*70}")
        ok = policy.evaluate("token.scan", "read")
        print(f"  token.scan        -> {ok['effect'].upper()}  (rule={ok['rule']})")
        print(f"    reason: {ok['reason']}")
        blocked = policy.evaluate("swap.execute", "value-moving", {"amount_usd": 500})
        print(f"  swap.execute      -> {blocked['effect'].upper()}  (rule={blocked['rule']})")
        print(f"    reason: {blocked['reason']}")
        with open(os.path.join(REPORTS, "policy_audit.json"), "w") as f:
            f.write(policy.audit_json())
        print("\n  -> audit log saved: reports/policy_audit.json")

        print(f"\n{'='*70}\nDemo complete. SENTINEL is read-only by policy: it scans, scores,\nand reports — it never signs and never moves funds.\n{'='*70}")

    transcript = buf.getvalue()
    with open(os.path.join(HERE, "demo_transcript.txt"), "w") as f:
        f.write(transcript)
    print(transcript)
    print(f"[demo] transcript written to {os.path.join(HERE, 'demo_transcript.txt')}")


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main()
