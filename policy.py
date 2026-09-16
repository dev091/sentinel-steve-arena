"""
SENTINEL policy engine — Bento-style local policy layer.

Every agent action is evaluated against an explicit policy BEFORE execution.
Read-only scans are auto-allowed. Anything value-moving requires explicit
approval and is BLOCKED by default. Decisions are logged as audit records.

This mirrors the Bento Guard integration pattern required by the OOBE bounty
spec: "Use Bento Guard as a policy layer before sensitive actions... Show at
least one allowed action and one blocked or escalated action."
"""

import json
import time

# Policy: explicit, auditable, deny-by-default for value movement.
POLICY = {
    "version": "1.0",
    "rules": [
        {"id": "read.scan", "match": {"action": "token.scan"},
         "effect": "allow", "reason": "read-only public data; no signing, no spend"},
        {"id": "read.market", "match": {"action": "market.quote"},
         "effect": "allow", "reason": "read-only public data"},
        {"id": "deny.value-move", "match": {"category": "value-moving"},
         "effect": "deny", "reason": "agent holds no keys; value movement requires explicit user approval in Steve"},
        {"id": "deny.sign", "match": {"action": "transaction.sign"},
         "effect": "deny", "reason": "signing boundary: only the user-controlled wallet signs"},
        {"id": "limit.report-size", "match": {"action": "report.publish"},
         "effect": "allow_if", "condition": "payload_kb <= 256",
         "reason": "keep reports small and auditable"},
    ],
}

AUDIT_LOG = []


def evaluate(action: str, category: str = "read", context: dict | None = None) -> dict:
    """Evaluate an action against policy. Returns the decision record."""
    ctx = context or {}
    decision = {"effect": "deny", "rule": "default-deny", "reason": "no matching allow rule"}
    for rule in POLICY["rules"]:
        m = rule["match"]
        if "action" in m and m["action"] != action:
            continue
        if "category" in m and m["category"] != category:
            continue
        if rule["effect"] == "allow_if":
            kb = ctx.get("payload_kb", 0)
            if kb <= 256:
                decision = {"effect": "allow", "rule": rule["id"], "reason": rule["reason"]}
            else:
                decision = {"effect": "deny", "rule": rule["id"],
                            "reason": f"payload {kb}kb exceeds 256kb cap"}
        else:
            decision = {"effect": rule["effect"], "rule": rule["id"], "reason": rule["reason"]}
        break
    record = {
        "ts": int(time.time()),
        "action": action,
        "category": category,
        **decision,
    }
    AUDIT_LOG.append(record)
    return record


def audit_json() -> str:
    return json.dumps(AUDIT_LOG, indent=2)


if __name__ == "__main__":
    # Demonstrate: one allowed action, one blocked action (bounty spec 10.2)
    print(json.dumps(evaluate("token.scan", "read"), indent=2))
    print(json.dumps(evaluate("swap.execute", "value-moving",
                             {"mint": "So11111111111111111111111111111111111111112"}), indent=2))
