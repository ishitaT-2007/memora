from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import get_settings

settings = get_settings()
MOCK_PATH = Path(__file__).resolve().parents[1] / "data" / "hindsight_mock.json"


@dataclass
class RecalledMemory:
    id: str
    text: str
    memory_type: str
    account_id: str
    source_ref: str
    score: float
    status: str = "verified"
    scope: str = "account"


class HindsightAdapter:
    """Isolates Hindsight. Mock mode keeps a local retain/recall store."""

    def __init__(self) -> None:
        self.mode = (settings.hindsight_mode or "mock").lower()
        self.available = True
        self.last_error: str | None = None
        self._store: dict[str, list[dict[str, Any]]] = {}
        if self.mode == "mock":
            self._load()

    def health(self) -> dict[str, Any]:
        if self.mode != "hindsight":
            return {"ok": True, "mode": self.mode}
        try:
            import httpx

            headers = {}
            if settings.hindsight_api_key:
                headers["Authorization"] = f"Bearer {settings.hindsight_api_key}"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{settings.hindsight_base_url.rstrip('/')}/health", headers=headers)
            return {"ok": response.status_code < 500, "mode": "hindsight", "status_code": response.status_code}
        except Exception as exc:  # pragma: no cover - network
            return {"ok": False, "mode": "hindsight", "error": str(exc)}

    def bank_id(self, account_id: str) -> str:
        return f"accrue-{account_id}"

    def retain(
        self,
        *,
        account_id: str,
        content: str,
        memory_id: str,
        memory_type: str,
        source_ref: str,
        scope: str,
        timestamp: str | None = None,
    ) -> None:
        payload = {
            "id": memory_id,
            "account_id": account_id,
            "text": content,
            "memory_type": memory_type,
            "source_ref": source_ref,
            "scope": scope,
            "timestamp": timestamp or "",
        }
        if self.mode == "hindsight":
            self._retain_live(account_id, payload)
            return
        bank = self.bank_id(account_id)
        items = self._store.setdefault(bank, [])
        items[:] = [item for item in items if item["id"] != memory_id]
        items.append(payload)
        self._save()

    def recall(self, *, account_id: str, query: str, include_comparable: bool = True) -> list[RecalledMemory]:
        self.last_error = None
        if self.mode == "hindsight":
            try:
                return self._recall_live(account_id, query)
            except Exception as exc:  # pragma: no cover - network
                self.available = False
                self.last_error = str(exc)
                return []
        results: list[RecalledMemory] = []
        banks = [self.bank_id(account_id)]
        if include_comparable:
            banks.extend(key for key in self._store if key != self.bank_id(account_id))
        tokens = _tokens(query)
        for bank in banks:
            for item in self._store.get(bank, []):
                if item["account_id"] != account_id and item.get("scope") != "comparable":
                    continue
                score = _overlap(tokens, _tokens(item["text"] + " " + item.get("memory_type", "")))
                if item["account_id"] == account_id:
                    score += 0.15
                if score <= 0:
                    continue
                results.append(
                    RecalledMemory(
                        id=item["id"],
                        text=item["text"],
                        memory_type=item["memory_type"],
                        account_id=item["account_id"],
                        source_ref=item.get("source_ref", ""),
                        score=round(score, 3),
                        scope=item.get("scope", "account"),
                    )
                )
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:18]

    def _retain_live(self, account_id: str, payload: dict[str, Any]) -> None:
        from hindsight_client import Hindsight

        client = Hindsight(
            base_url=settings.hindsight_base_url,
            timeout=float(settings.hindsight_timeout_seconds),
            api_key=settings.hindsight_api_key or None,
        )
        client.retain(
            bank_id=self.bank_id(account_id),
            content=payload["text"],
            context=payload["memory_type"],
            metadata={
                "memory_id": payload["id"],
                "account_id": account_id,
                "source_ref": payload["source_ref"],
                "scope": payload["scope"],
            },
            retain_async=False,
        )

    def _recall_live(self, account_id: str, query: str) -> list[RecalledMemory]:
        from hindsight_client import Hindsight

        client = Hindsight(
            base_url=settings.hindsight_base_url,
            timeout=float(settings.hindsight_timeout_seconds),
            api_key=settings.hindsight_api_key or None,
        )
        response = client.recall(bank_id=self.bank_id(account_id), query=query, budget="high")
        results: list[RecalledMemory] = []
        for index, item in enumerate(getattr(response, "results", []) or []):
            text = getattr(item, "text", "") or str(item)
            results.append(
                RecalledMemory(
                    id=getattr(item, "id", f"hs_{index}"),
                    text=text,
                    memory_type=str(getattr(item, "type", "world")),
                    account_id=account_id,
                    source_ref="",
                    score=1.0 - (index * 0.03),
                )
            )
        return results

    def _load(self) -> None:
        if MOCK_PATH.exists():
            self._store = json.loads(MOCK_PATH.read_text(encoding="utf-8"))
        else:
            self._store = {}

    def _save(self) -> None:
        MOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        MOCK_PATH.write_text(json.dumps(self._store, indent=2), encoding="utf-8")

    def reset_mock(self) -> None:
        self._store = {}
        if MOCK_PATH.exists():
            MOCK_PATH.unlink()


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9$]+", text.lower()) if len(token) > 2}


def _overlap(query_tokens: set[str], doc_tokens: set[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    inter = len(query_tokens & doc_tokens)
    return inter / max(1, len(query_tokens))


hindsight = HindsightAdapter()
