from typing import List, Dict, Optional
from ..api import create_lightspeed_request


def create_webhook(topic: str, url: str, active: bool = True) -> Dict:
    payload = {"type": topic, "url": url, "active": active}
    r = create_lightspeed_request(method="POST", endpoint="webhooks", json=payload)
    return r.json()

def update_webhook(webhook_id: str, *, url: Optional[str] = None, active: Optional[bool] = None) -> Dict:
    body = {}
    if url is not None: body["url"] = url
    if active is not None: body["active"] = active
    r = create_lightspeed_request("PUT", f"webhooks/{webhook_id}", json=body)
    return r.json()

def list_webhooks() -> List[Dict]:
    r = create_lightspeed_request("GET", "webhooks")
    print(f"Webhooks response: {r.status_code} {r.text}")
    data = r.json()

    # Already a list?
    if isinstance(data, list):
        return data

    # Common wrapper shapes
    if isinstance(data, dict):
        if isinstance(data.get("webhooks"), list):
            return data["webhooks"]
        if isinstance(data.get("data"), list):          # sometimes APIs use 'data'
            return data["data"]
        if isinstance(data.get("webhook"), dict):       # single object case
            return [data["webhook"]]
        if isinstance(data.get("webhooks"), dict):      # dict keyed by id → convert to list
            return list(data["webhooks"].values())

    # Last resort: normalize a single dict into a list
    if isinstance(data, dict):
        return [data]

    raise ValueError(f"Unexpected /webhooks response shape: {type(data)} -> {data!r}")

def delete_webhook(webhook_id: str) -> None:
    create_lightspeed_request("DELETE", f"webhooks/{webhook_id}")
    

def find_webhook_by_type(topic: str) -> Optional[Dict]:
    webhooks = list_webhooks()
    for wh in webhooks:
        if isinstance(wh, dict) and wh.get("type") == topic:
            return wh
    return None


def ensure_webhook(topic: str, url: str, active: bool = True) -> Dict:
    """
    Idempotent: create if missing; update if exists and differs.
    """
    current = find_webhook_by_type(topic)
    if not current:
        return create_webhook(topic, url, active)
    needs_update = (current.get("url") != url) or (bool(current.get("active")) != bool(active))
    if needs_update:
        return update_webhook(current["id"], url=url, active=active)
    return current

def ensure_many(desired: Dict[str, str], active: bool = True) -> Dict[str, Dict]:
    """
    desired = { "inventory.update": "https://.../webhooks/lightspeed/inventory/",
                "product.update":   "https://.../webhooks/lightspeed/product/",
                "customer.update":  "https://.../webhooks/lightspeed/customer/",
                "sale.update":      "https://.../webhooks/lightspeed/sale/" }
    """
    out = {}
    for topic, url in desired.items():
        out[topic] = ensure_webhook(topic, url, active=active)
    return out