"""Payload-free, evidence-only managed-flow observations for P8.3."""

from __future__ import annotations

import contextlib
import contextvars
import json
import os
import re
import secrets
import threading
from collections import Counter
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlsplit

FLOW_PREFIX = "LOCUS_FLOW_V1 "
FLOW_HEADER = "X-LOCUS-Flow-Context"
TRACE_POLICY_ID = "LOCUS-managed-flow-trace-policy-v1"
_CONTEXT = contextvars.ContextVar("locus_flow_context", default="")
_CONTEXT_RE = re.compile(
    r"NF(?:0[1-9]|1[0-2]):(?:yi|appss)-(?:2of3|3of5)|NF(?:0[7-9]|1[0-2]):managed-common\Z"
)
_ROLE_RE = re.compile(
    r"(?:browser|manager-ui|manager-controller|managed-client|admission|operator|resolver|storage-gateway|provider|docker-engine|party[1-5])\Z"
)
_lock = threading.Lock()
_role = ""
_boot = secrets.token_hex(8)
_sequence = 0

RPC_CATEGORIES = {
    ("admission", "/v1/issue"): "admission-issue",
    ("operator", "/v1/sign"): "operator-sign",
    ("operator", "/v1/discovery/publish"): "discovery-publish",
    ("operator", "/v1/discovery/read"): "discovery-read",
    ("storage-gateway", "/v1/execute"): "storage-execute",
    ("resolver", "/v1/resolve"): "resolver-resolve",
    ("manager-controller", "/v1/status"): "manager-status",
    ("manager-controller", "/v1/client/create"): "client-create",
    ("manager-controller", "/v1/container/action"): "container-action",
    ("manager-controller", "/v1/client/destroy"): "client-destroy",
    ("manager-controller", "/v1/client/self-destroy"): "self-destroy",
    ("manager-controller", "/v1/system/stop"): "system-stop",
}
PARTY_CATEGORIES = {
    "/v1/authorize": "authorize",
    "/v1/yi/enroll": "yi-enroll",
    "/v1/yi/prepare": "yi-prepare",
    "/v1/yi/respond": "yi-respond",
    "/v1/appss/initialize": "appss-initialize",
    "/v1/appss/install": "appss-install",
    "/v1/appss/evaluate": "appss-evaluate",
    "/v1/current/install": "current-install",
    "/v1/current/read": "current-read",
    "/v1/current/retire": "current-retire",
    "/v1/inspect": "party-inspect",
}
MANAGER_HTTP_CATEGORIES = {
    "/api/manager/v1/session": "manager-session",
    "/api/manager/v1/status": "manager-status",
    "/api/manager/v1/clients": "client-create",
    "/api/manager/v1/container-action": "container-action",
    "/api/manager/v1/client-destroy": "client-destroy",
    "/api/manager/v1/system-stop": "system-stop",
}
CLIENT_HTTP_CATEGORIES = {
    "/api/v2/session": "client-session",
    "/api/v2/catalog": "client-catalog",
    "/api/v2/key/generate": "key-generate",
    "/api/v2/preview-policy": "policy-preview",
    "/api/v2/enroll": "enroll",
    "/api/v2/package/export": "package-export",
    "/api/v2/package/import": "package-import",
    "/api/v2/recover": "recover",
    "/api/v2/key/reveal": "key-reveal",
    "/api/v2/self-destroy": "self-destroy",
}
DOCKER_CATEGORIES = {
    ("GET", "/version"): "engine-version",
    ("GET", "/containers/json"): "container-list",
    ("GET", "/containers/"): "container-inspect",
    ("GET", "/images/"): "image-inspect",
    ("POST", "/containers/create"): "container-create",
    ("POST", "/containers/", "/start"): "container-start",
    ("POST", "/containers/", "/stop"): "container-stop",
    ("POST", "/containers/", "/restart"): "container-restart",
    ("POST", "/containers/", "/kill"): "container-kill",
    ("DELETE", "/containers/"): "container-remove",
    ("GET", "/networks"): "network-list",
    ("POST", "/networks/", "/connect"): "network-connect",
    ("DELETE", "/networks/"): "network-remove",
}


class FlowAuditError(ValueError):
    """An evidence-only flow observation violated its frozen vocabulary."""


EVENT_FIELDS = {
    "boot",
    "category",
    "context",
    "observation",
    "receiver",
    "request_bytes",
    "response_bytes",
    "result",
    "sender",
    "sequence",
    "trace_policy_id",
}
PROHIBITED_EDGES = {
    ("browser", "admission"),
    ("browser", "operator"),
    ("browser", "resolver"),
    ("browser", "storage-gateway"),
    ("browser", "provider"),
    ("browser", "docker-engine"),
    ("managed-client", "manager-ui"),
    ("managed-client", "provider"),
    ("manager-ui", "managed-client"),
    ("manager-ui", "docker-engine"),
}


def enabled() -> bool:
    return os.environ.get("LOCUS_FLOW_AUDIT") == "1"


def configure_role(role: str) -> None:
    global _role
    if _ROLE_RE.fullmatch(role) is None:
        raise FlowAuditError("unknown flow role")
    _role = role


def current_context() -> str:
    return _CONTEXT.get()


@contextlib.contextmanager
def flow_context(value: str | None) -> Iterator[None]:
    context = value or ""
    if context and _CONTEXT_RE.fullmatch(context) is None:
        raise FlowAuditError("invalid flow context")
    token = _CONTEXT.set(context)
    try:
        yield
    finally:
        _CONTEXT.reset(token)


def rpc_category(receiver: str, path: str) -> str:
    if receiver.startswith("party"):
        category = PARTY_CATEGORIES.get(path)
    else:
        category = RPC_CATEGORIES.get((receiver, path))
    if category is None:
        raise FlowAuditError("unknown RPC category")
    return category


def http_category(receiver: str, path: str) -> str:
    parsed = urlsplit(path).path
    mapping = (
        MANAGER_HTTP_CATEGORIES if receiver == "manager-ui" else CLIENT_HTTP_CATEGORIES
    )
    category = mapping.get(parsed)
    if category is None:
        raise FlowAuditError("unknown browser category")
    return category


def docker_category(method: str, path: str) -> str:
    logical = re.sub(r"^/v\d+\.\d+", "", urlsplit(path).path)
    for key, category in DOCKER_CATEGORIES.items():
        if key[0] != method:
            continue
        if len(key) == 2 and (logical == key[1] or logical.startswith(key[1])):
            return category
        if len(key) == 3 and logical.startswith(key[1]) and logical.endswith(key[2]):
            return category
    raise FlowAuditError("unknown Docker category")


def outcome(status: int) -> str:
    if 200 <= status < 300:
        return "success"
    return "unavailable" if status >= 500 else "rejected"


def emit(
    *,
    sender: str,
    receiver: str,
    category: str,
    request_bytes: int,
    response_bytes: int,
    result: str,
    observation: str,
) -> dict[str, Any] | None:
    global _sequence
    context = current_context()
    if not enabled() or not context:
        return None
    if _ROLE_RE.fullmatch(sender) is None or _ROLE_RE.fullmatch(receiver) is None:
        raise FlowAuditError("unknown flow edge")
    if (
        receiver
        not in {
            "manager-ui",
            "managed-client",
            "provider",
            "docker-engine",
        }
        and rpc_category(receiver, _category_probe_path(receiver, category)) != category
    ):
        raise FlowAuditError("unknown flow category")
    if observation not in {"sender", "receiver"} or result not in {
        "success",
        "rejected",
        "unavailable",
    }:
        raise FlowAuditError("invalid flow observation")
    if any(
        not isinstance(value, int) or value < 0 or value > 4 * 1024 * 1024
        for value in (request_bytes, response_bytes)
    ):
        raise FlowAuditError("invalid flow byte count")
    with _lock:
        _sequence += 1
        sequence = _sequence
    event = {
        "boot": _boot,
        "category": category,
        "context": context,
        "observation": observation,
        "receiver": receiver,
        "request_bytes": request_bytes,
        "response_bytes": response_bytes,
        "result": result,
        "sender": sender,
        "sequence": sequence,
        "trace_policy_id": TRACE_POLICY_ID,
    }
    print(
        FLOW_PREFIX + json.dumps(event, sort_keys=True, separators=(",", ":")),
        flush=True,
    )
    return event


def _category_probe_path(receiver: str, category: str) -> str:
    for (candidate_receiver, path), candidate in RPC_CATEGORIES.items():
        if candidate_receiver == receiver and candidate == category:
            return path
    if receiver.startswith("party"):
        for path, candidate in PARTY_CATEGORIES.items():
            if candidate == category:
                return path
    raise FlowAuditError("unknown RPC category")


def configured_role() -> str:
    if not _role:
        raise FlowAuditError("flow role was not configured")
    return _role


def validate_event(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != EVENT_FIELDS:
        raise FlowAuditError("flow event field set changed")
    if value["trace_policy_id"] != TRACE_POLICY_ID:
        raise FlowAuditError("flow trace policy changed")
    if (
        not isinstance(value["boot"], str)
        or re.fullmatch(r"[0-9a-f]{16}", value["boot"]) is None
    ):
        raise FlowAuditError("invalid flow boot identifier")
    if (
        not isinstance(value["context"], str)
        or _CONTEXT_RE.fullmatch(value["context"]) is None
    ):
        raise FlowAuditError("invalid flow context")
    for field in ("sender", "receiver"):
        if (
            not isinstance(value[field], str)
            or _ROLE_RE.fullmatch(value[field]) is None
        ):
            raise FlowAuditError("unknown flow role")
    if (value["sender"], value["receiver"]) in PROHIBITED_EDGES:
        raise FlowAuditError("prohibited flow edge observed")
    if value["observation"] not in {"sender", "receiver"} or value["result"] not in {
        "success",
        "rejected",
        "unavailable",
    }:
        raise FlowAuditError("invalid flow event enum")
    for field in ("request_bytes", "response_bytes"):
        if (
            not isinstance(value[field], int)
            or value[field] < 0
            or value[field] > 4 * 1024 * 1024
        ):
            raise FlowAuditError("flow byte bound failed")
    if not isinstance(value["sequence"], int) or value["sequence"] < 1:
        raise FlowAuditError("invalid flow sequence")
    receiver = str(value["receiver"])
    category = str(value["category"])
    allowed = (
        set(RPC_CATEGORIES.values())
        | set(PARTY_CATEGORIES.values())
        | set(MANAGER_HTTP_CATEGORIES.values())
        | set(CLIENT_HTTP_CATEGORIES.values())
        | set(DOCKER_CATEGORIES.values())
        | {"object-create", "object-read", "object-cas", "object-delete"}
    )
    if category not in allowed:
        raise FlowAuditError("unknown flow category")
    if receiver == "resolver" and value["context"].endswith("2of3"):
        raise FlowAuditError("NoResolver arm contacted resolver")
    return value


def parse_events(
    logs: list[str], *, extra_events: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Parse bounded prefixed events; deduplicate repeated log snapshots."""

    events: dict[tuple[str, int], dict[str, Any]] = {}
    for raw in logs:
        if len(raw.encode("utf-8", errors="replace")) > 32 * 1024 * 1024:
            raise FlowAuditError("flow log input is too large")
        for line in raw.splitlines():
            for encoded in line.split(FLOW_PREFIX)[1:]:
                if len(encoded) > 4096:
                    raise FlowAuditError("flow event is too large")
                try:
                    value, end = json.JSONDecoder().raw_decode(encoded)
                    if encoded[end:].strip():
                        raise FlowAuditError("flow event has trailing data")
                    event = validate_event(value)
                except FlowAuditError:
                    raise
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise FlowAuditError(
                        f"invalid flow event framing at {getattr(exc, 'pos', -1)}"
                    ) from exc
                key = (event["boot"], event["sequence"])
                if key in events and events[key] != event:
                    raise FlowAuditError("conflicting duplicate flow sequence")
                events[key] = event
    for event in extra_events or []:
        checked = validate_event(event)
        key = (checked["boot"], checked["sequence"])
        if key in events and events[key] != checked:
            raise FlowAuditError("conflicting extra flow sequence")
        events[key] = checked
    by_boot: dict[str, list[int]] = {}
    for boot, sequence in events:
        by_boot.setdefault(boot, []).append(sequence)
    for sequences in by_boot.values():
        ordered = sorted(sequences)
        if ordered != list(range(1, max(ordered) + 1)):
            raise FlowAuditError("flow sequence gap")
    return [events[key] for key in sorted(events)]


def aggregate_events(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Reconcile observations and return the only retainable aggregates."""

    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for raw in events:
        event = validate_event(raw)
        key = (event["context"], event["sender"], event["receiver"], event["category"])
        group = grouped.setdefault(key, {"sender": [], "receiver": []})
        group[event["observation"]].append(event)
    result: dict[str, list[dict[str, Any]]] = {}
    for (context, sender, receiver, category), observations in grouped.items():
        sender_items = observations["sender"]
        receiver_items = observations["receiver"]
        fixed_available = receiver in {"provider", "docker-engine"}
        if fixed_available:
            if not sender_items or receiver_items:
                raise FlowAuditError("fixed-available observation boundary changed")
            selected = sender_items
            reconciliation = "fixed-available"
        else:
            if not sender_items:
                raise FlowAuditError("flow sender observation missing")

            def projection(item: dict[str, Any]) -> tuple[int, int, str]:
                return (
                    int(item["request_bytes"]),
                    int(item["response_bytes"]),
                    str(item["result"]),
                )

            sender_projection = Counter(map(projection, sender_items))
            receiver_projection = Counter(map(projection, receiver_items))
            unmatched_receiver = receiver_projection - sender_projection
            unmatched_sender = sender_projection - receiver_projection
            if unmatched_receiver or any(
                item[2] != "unavailable" for item in unmatched_sender.elements()
            ):
                raise FlowAuditError(
                    "flow observations do not reconcile: "
                    f"{context}/{sender}/{receiver}/{category}/"
                    f"count={len(sender_items)}:{len(receiver_items)}/"
                    f"request={sum(int(item['request_bytes']) for item in sender_items)}:"
                    f"{sum(int(item['request_bytes']) for item in receiver_items)}/"
                    f"response={sum(int(item['response_bytes']) for item in sender_items)}:"
                    f"{sum(int(item['response_bytes']) for item in receiver_items)}"
                )
            selected = sender_items
            reconciliation = "matched"
        contact = {
            "category": category,
            "receiver_role": "party" if receiver.startswith("party") else receiver,
            "reconciliation": reconciliation,
            "rejected_count": sum(item["result"] == "rejected" for item in selected),
            "request_body_bytes": sum(item["request_bytes"] for item in selected),
            "request_count": len(selected),
            "response_body_bytes": sum(item["response_bytes"] for item in selected),
            "sender_role": "party" if sender.startswith("party") else sender,
            "success_count": sum(item["result"] == "success" for item in selected),
            "unavailable_count": sum(
                item["result"] == "unavailable" for item in selected
            ),
        }
        result.setdefault(context, []).append(contact)
    for contacts in result.values():
        contacts.sort(
            key=lambda item: (
                item["sender_role"],
                item["receiver_role"],
                item["category"],
            )
        )
    return result


__all__ = [
    "FLOW_HEADER",
    "FLOW_PREFIX",
    "TRACE_POLICY_ID",
    "FlowAuditError",
    "configure_role",
    "configured_role",
    "current_context",
    "docker_category",
    "emit",
    "enabled",
    "flow_context",
    "http_category",
    "outcome",
    "rpc_category",
    "aggregate_events",
    "parse_events",
    "validate_event",
]
