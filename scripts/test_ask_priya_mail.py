"""Test Accrue company Q&A — especially Priya's live mail vs old memory."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx

from app.data.corpus import DEMO_ESCALATION, INJECTION_ESCALATION

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def login(client: httpx.Client) -> dict:
    response = client.post(
        f"{BASE}/api/auth/login",
        json={"email": "csm@accrue.demo", "password": "AccrueDemo!2026"},
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def ask(client: httpx.Client, headers: dict, query: str, current_mail: str = "") -> dict:
    response = client.post(
        f"{BASE}/api/accounts/acc_acme/ask",
        headers=headers,
        json={"query": query, "current_mail": current_mail},
    )
    print(f"\nQ: {query}\nstatus={response.status_code}")
    if response.status_code != 200:
        print(response.text)
        return {"ok": False, "body": response.text}
    body = response.json()
    print(body.get("answer", "")[:600])
    return {"ok": True, **body}


def main() -> None:
    client = httpx.Client(timeout=30.0)
    headers = login(client)
    cases = []

    mail = ask(client, headers, "what is priya telling in mail", DEMO_ESCALATION)
    answer = (mail.get("answer") or "").lower()
    cases.append(
        (
            "live_mail_not_old_memory",
            mail["ok"]
            and "third outage" in answer
            and "we are done" in answer
            and "12 mar 2026" not in answer
            and "q2 saml" not in answer,
        )
    )

    promise = ask(client, headers, "What did we promise Priya?")
    promise_text = (promise.get("answer") or "").lower()
    cases.append(
        (
            "promise_from_memory",
            promise["ok"] and ("15 minutes" in promise_text or "dedicated" in promise_text),
        )
    )

    injection = ask(client, headers, "what is priya telling in this email", INJECTION_ESCALATION)
    inj = (injection.get("answer") or "").lower()
    cases.append(
        (
            "mail_ignores_injection_as_history",
            injection["ok"] and "third outage" in inj and "legal already approved" in inj,
        )
    )

    missing = ask(client, headers, "what is priya telling in mail", "")
    cases.append(("no_mail_says_unknown_or_latest", missing["ok"]))

    print("\n" + json.dumps({"results": [{"name": name, "pass": ok} for name, ok in cases]}, indent=2))
    failed = [name for name, ok in cases if not ok]
    if failed:
        raise SystemExit(f"FAILED: {failed}")
    print("All ask-mail checks passed.")


if __name__ == "__main__":
    main()
