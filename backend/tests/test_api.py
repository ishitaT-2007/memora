from fastapi.testclient import TestClient

from app.data.corpus import DEMO_ESCALATION, INJECTION_ESCALATION
from app.main import app

client = TestClient(app)

CSM = {"email": "csm@accrue.demo", "password": "AccrueDemo!2026"}
ADMIN = {"email": "admin@accrue.demo", "password": "AccrueAdmin!2026"}


def login(user=None) -> str:
    response = client.post("/api/auth/login", json=user or CSM)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"]["ok"] is True


def test_login_rejects_bad_password():
    response = client.post("/api/auth/login", json={"email": CSM["email"], "password": "nope"})
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_CREDENTIALS"


def test_accounts_require_auth():
    response = client.get("/api/accounts")
    assert response.status_code == 401


def test_list_accounts():
    token = login()
    response = client.get("/api/accounts", headers=auth_headers(token))
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["accounts"]}
    assert "acc_acme" in ids
    assert "acc_northstar" in ids


def test_account_context_has_commitments():
    token = login()
    response = client.get("/api/accounts/acc_acme/context", headers=auth_headers(token))
    body = response.json()
    assert any("SSO" in row["description"] or "SAML" in row["description"] for row in body["commitments"])
    assert any(row["status"] == "slipped" for row in body["commitments"])


def test_analyze_validation():
    token = login()
    response = client.post(
        "/api/escalations/analyze",
        headers=auth_headers(token),
        json={"account_id": "acc_acme", "escalation_text": "too short"},
    )
    assert response.status_code == 422


def test_unknown_account_not_guessed():
    token = login()
    response = client.post(
        "/api/escalations/analyze",
        headers=auth_headers(token),
        json={"account_id": "acc_missing", "escalation_text": DEMO_ESCALATION},
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "ACCOUNT_NOT_FOUND"


def test_happy_path_acme_demo():
    token = login()
    response = client.post(
        "/api/escalations/analyze",
        headers=auth_headers(token),
        json={"account_id": "acc_acme", "escalation_text": DEMO_ESCALATION, "severity": "P1"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    output = body["output"]
    assert output["memory_limited"] is False
    joined = " ".join(output["brief"]).lower()
    assert "priya" in joined or "acme" in joined
    assert any("credit" in item["action"].lower() for item in output["dont"])
    assert any("sso" in item["action"].lower() for item in output["dont"])
    assert "90%" not in output["reply_draft"]
    assert body["review_state"] == "human_review_required"
    assert output["memory_ids"]
    for fact in output["known_facts"]:
        assert fact["source_ids"]


def test_memory_limited_omits_history():
    token = login()
    response = client.post(
        "/api/escalations/analyze",
        headers=auth_headers(token),
        json={
            "account_id": "acc_acme",
            "escalation_text": DEMO_ESCALATION,
            "memory_mode": "limited",
        },
    )
    output = response.json()["output"]
    assert output["memory_limited"] is True
    assert output["known_facts"] == []
    assert "invent" in " ".join(item["action"].lower() for item in output["dont"])


def test_prompt_injection_is_ignored():
    token = login()
    response = client.post(
        "/api/escalations/analyze",
        headers=auth_headers(token),
        json={"account_id": "acc_acme", "escalation_text": INJECTION_ESCALATION},
    )
    output = response.json()["output"]
    draft = output["reply_draft"].lower()
    assert "90%" not in draft
    assert "full refund" not in draft
    assert "live tomorrow" not in draft
    assert output["classification"]["prompt_injection_suspected"] is True


def test_correction_preview_does_not_write_and_confirm_persists():
    token = login()
    first = client.post(
        "/api/escalations/analyze",
        headers=auth_headers(token),
        json={"account_id": "acc_acme", "escalation_text": DEMO_ESCALATION},
    ).json()
    escalation_id = first["escalation_id"]
    preview = client.post(
        f"/api/escalations/{escalation_id}/corrections/preview",
        headers=auth_headers(token),
        json={
            "proposed_memory": "Never offer credits to Priya; escalate to engineering first.",
            "memory_type": "team_correction",
            "scope": "account",
        },
    )
    assert preview.status_code == 200
    assert preview.json()["writes_memory"] is False
    correction_id = preview.json()["correction_id"]

    confirm = client.post(
        f"/api/escalations/{escalation_id}/corrections/confirm",
        headers={**auth_headers(token), "Idempotency-Key": "idem-1"},
        json={"correction_id": correction_id, "confirm": True},
    )
    assert confirm.status_code == 200
    memory_id = confirm.json()["memory_id"]

    replay = client.post(
        f"/api/escalations/{escalation_id}/corrections/confirm",
        headers={**auth_headers(token), "Idempotency-Key": "idem-1"},
        json={"correction_id": correction_id, "confirm": True},
    )
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["memory_id"] == memory_id

    detail = client.get(f"/api/memories/{memory_id}", headers=auth_headers(token))
    assert detail.status_code == 200
    assert "engineering first" in detail.json()["memory"]["text"].lower()

    second = client.post(
        "/api/escalations/analyze",
        headers=auth_headers(token),
        json={"account_id": "acc_acme", "escalation_text": DEMO_ESCALATION},
    ).json()["output"]
    blob = " ".join(second["brief"] + [item["text"] for item in second["known_facts"]]).lower()
    assert "engineering first" in blob or memory_id in second["memory_ids"] or any(
        "credits to priya" in item["text"].lower() for item in second["known_facts"]
    )


def test_team_scope_requires_admin():
    token = login()
    first = client.post(
        "/api/escalations/analyze",
        headers=auth_headers(token),
        json={"account_id": "acc_acme", "escalation_text": DEMO_ESCALATION},
    ).json()
    response = client.post(
        f"/api/escalations/{first['escalation_id']}/corrections/preview",
        headers=auth_headers(token),
        json={"proposed_memory": "Team-wide: never lead with credits on reliability.", "scope": "team"},
    )
    assert response.status_code == 403


def test_source_details_and_export():
    token = login()
    analyzed = client.post(
        "/api/escalations/analyze",
        headers=auth_headers(token),
        json={"account_id": "acc_acme", "escalation_text": DEMO_ESCALATION},
    ).json()
    source = client.get("/api/sources/src_acme_sso", headers=auth_headers(token))
    assert source.status_code == 200
    assert "SSO" in source.json()["body"] or "SAML" in source.json()["body"]
    exported = client.get(
        f"/api/escalations/{analyzed['escalation_id']}/export",
        headers=auth_headers(token),
    )
    assert exported.status_code == 200
    assert "DRAFT" in exported.json()["text"]


def test_admin_reset_forbidden_to_csm():
    token = login()
    response = client.post("/api/admin/reset-demo", headers=auth_headers(token))
    assert response.status_code == 403


def test_ask_company_memory():
    token = login()
    response = client.post(
        "/api/accounts/acc_acme/ask",
        headers=auth_headers(token),
        json={"query": "What did we promise Priya?"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["unknown"] is False
    assert "priya" in body["answer"].lower()
    assert "15 minutes" in body["answer"] or "dedicated" in body["answer"].lower()
    missing = client.post(
        "/api/accounts/acc_acme/ask",
        headers=auth_headers(token),
        json={"query": "What is their office dog's name?"},
    )
    assert missing.status_code == 200
    assert missing.json()["unknown"] is True


def test_ask_priya_mail_uses_current_email():
    token = login()
    from app.data.corpus import DEMO_ESCALATION

    response = client.post(
        "/api/accounts/acc_acme/ask",
        headers=auth_headers(token),
        json={"query": "what is priya telling in mail", "current_mail": DEMO_ESCALATION},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    answer = body["answer"].lower()
    assert "third outage" in answer
    assert "we are done" in answer
    assert "checkout api" in answer
    assert "q2 saml sso" not in answer
    assert "12 mar 2026" not in answer
    assert "current_mail" in body["citations"]
    source = client.get("/api/sources/current_mail", headers=auth_headers(token))
    assert source.status_code == 200, source.text
    assert source.headers.get("content-type", "").startswith("application/json")
    assert source.json()["id"] == "current_mail"
    assert source.json()["body"]


def test_admin_can_reset():
    token = login(ADMIN)
    response = client.post("/api/admin/reset-demo", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["ok"] is True
