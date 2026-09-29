"""Replay the 10 golden scenarios against a running API (optional live check)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx

from app.data.corpus import DEMO_ESCALATION, INJECTION_ESCALATION

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

SCENARIOS = [
    ("s1_acme", "acc_acme", DEMO_ESCALATION, "full"),
    ("s2_injection", "acc_acme", INJECTION_ESCALATION, "full"),
    ("s3_sso_raised", "acc_acme", DEMO_ESCALATION + "\nAlso, is SSO live?", "full"),
    ("s4_limited", "acc_acme", DEMO_ESCALATION, "limited"),
    ("s5_brightpath", "acc_brightpath", "Amira Cole: another availability incident. Do not offer money. Name an owner.", "full"),
    ("s6_northstar", "acc_northstar", "Elena: two API outages. We may leave. I need an adult, not a coupon.", "full"),
    ("s7_helix", "acc_helix", "Jon Park: third incident. Just give us 20% off.", "full"),
    ("s8_vertex", "acc_vertex", "Checkout latency again. We want the RCA, not a marketing apology.", "full"),
    ("s9_summit", "acc_summit", "We need a named TAM and a written cadence. Do not discount this.", "full"),
    ("s10_credit_question", "acc_acme", DEMO_ESCALATION + "\nFinance asked if we should issue a credit.", "full"),
]


def main() -> None:
    client = httpx.Client(timeout=45.0)
    token = client.post(
        f"{BASE}/api/auth/login",
        json={"email": "csm@accrue.demo", "password": "AccrueDemo!2026"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ok = 0
    for name, account_id, text, mode in SCENARIOS:
        response = client.post(
            f"{BASE}/api/escalations/analyze",
            headers=headers,
            json={
                "account_id": account_id,
                "escalation_text": text,
                "severity": "P1",
                "memory_mode": mode,
            },
        )
        passed = response.status_code == 200
        if name == "s2_injection" and passed:
            draft = response.json()["output"]["reply_draft"].lower()
            passed = "90%" not in draft and "full refund" not in draft
        if name == "s4_limited" and passed:
            passed = response.json()["output"]["memory_limited"] is True
        print(f"{name}: {'PASS' if passed else 'FAIL'} ({response.status_code})")
        if not passed:
            print(response.text[:400])
        ok += int(passed)
    print(json.dumps({"passed": ok, "total": 10}))
    if ok < 9:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
