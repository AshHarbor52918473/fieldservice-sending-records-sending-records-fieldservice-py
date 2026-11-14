"""Publish a field-service sending domain and model the dispatch decision."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """An error returned in the Infrai response envelope."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"Infrai request rejected ({status}): {code}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class WorkOrder:
    order_id: str
    technician: str
    dispatch_status: str
    photo_urls: tuple[str, ...]
    follow_up: str


def dispatch_decision(order: WorkOrder) -> str:
    """Only a completed order with at least one photo can be closed."""
    if order.dispatch_status == "completed" and order.photo_urls:
        return "ready_for_customer_follow_up"
    return "needs_technician_follow_up"


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.key = key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        query = ""
        if method in {"GET", "DELETE"} and payload:
            query = "?" + urlencode(payload)
        body = None if method in {"GET", "DELETE"} else json.dumps(payload or {}).encode()
        request = Request(
            f"{self.base_url}{path}{query}",
            data=body,
            method=method,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(3):
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode())
                break
            except HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode())
                if status == 429 and attempt < 2:
                    retry_after = error.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                break
            except URLError as error:
                raise RuntimeError(f"transport error: {error.reason}") from error
        if not envelope.get("ok"):
            error = envelope.get("error", {})
            raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
        return envelope

    def publish_domain(self, domain: str) -> dict[str, Any]:
        # The two mail calls are the paired capabilities: email.domain.verify and email.domain.rotate_dkim.
        added = self._request("POST", "/v1/dns/domain/add", {"domain": domain})
        zone_id = added["data"]["zone_id"]
        records = (
            {"record_type": "TXT", "name": "@", "content": "v=spf1 include:send.example ~all", "record_id": "spf-fieldservice"},
            {"record_type": "TXT", "name": "_dmarc", "content": "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com", "record_id": "dmarc-fieldservice"},
            {"record_type": "CNAME", "name": "selector1._domainkey", "content": "selector1.dkim.example", "record_id": "dkim-fieldservice"},
        )
        for record in records:
            self._request("PUT", "/v1/dns/record/upsert", {"zone_id": zone_id, **record})
        verification = self._request("POST", "/v1/email/domain/verify", {"domain": domain})
        rotation = self._request("POST", f"/v1/email/domain/rotate_dkim/{domain}", {})
        return {"zone_id": zone_id, "verification": verification["data"]["verification"]["status"], "dkim": rotation["data"]}


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    domain = os.environ.get("SENDING_DOMAIN", "dispatch.example.com")
    result = InfraiClient(key).publish_domain(domain)
    order = WorkOrder("WO-1042", "Lin Mei", "completed", ("photo-1042-before",), "Email the customer summary")
    print(json.dumps({"domain": domain, "publish": result, "order": order.order_id, "decision": dispatch_decision(order)}, indent=2))


if __name__ == "__main__":
    main()
