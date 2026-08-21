"""Managed transient Client UI and API over the integrated protocol backend."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import secrets
import socket
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .admission import client_key_thumbprint
from .client_api import CLIENT_API_VERSION, ClientApiError
from .codec import encode
from .crypto import random_bytes
from .flow_audit import (
    FLOW_HEADER,
    configure_role,
    flow_context,
    http_category,
)
from .flow_audit import (
    emit as emit_flow,
)
from .flow_audit import (
    enabled as flow_enabled,
)
from .flow_audit import (
    outcome as flow_outcome,
)
from .integrated_client import (
    AuthenticatedRecoveryPackage,
    IntegratedResearchClientApi,
)
from .integrated_rpc import rpc_request
from .recovery_package import (
    MAX_RECOVERY_PACKAGE_BYTES,
    RECOVERY_PACKAGE_MEDIA_TYPE,
    RECOVERY_PACKAGE_VERSION,
)
from .redaction import validate_public_output

MANAGED_CLIENT_API_VERSION = "LOCUS-client-api-v2"
MANAGED_CLIENT_UI_PROFILE = "LOCUS-managed-client-ui-v1"
MANAGED_CLIENT_INSTANCE_PROFILE = "LOCUS-managed-client-instance-v1"
PERFORMANCE_INSTRUMENTATION_IDS = frozenset(
    {
        "LOCUS-managed-performance-instrumentation-v1",
        "LOCUS-managed-performance-instrumentation-v2",
    }
)
MAX_JSON_REQUEST_BYTES = 128 * 1024
MAX_ASSET_BYTES = 512 * 1024
MAX_CLIENT_OPERATIONS = 1024
MAX_RECOVERY_EXPORTS = 32
ASSET_ROOT = Path(__file__).resolve().parent / "client_assets"
_CLIENT_ID = re.compile(r"client-[0-9a-f]{16}\Z")
_OPERATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class ManagedClientError(ValueError):
    """A managed-client request failed its bounded local contract."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


@dataclass(frozen=True)
class ClientResponse:
    status: int
    content_type: str
    body: bytes
    transient_secret_path: bool = False
    content_disposition: str | None = None


def _raw_public(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def _fingerprint(private_key: bytes) -> str:
    public = (
        Ed25519PrivateKey.from_private_bytes(private_key)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )
    return hashlib.sha256(public).hexdigest()


def _exact(value: object, fields: set[str], category: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ManagedClientError(category)
    return cast(dict[str, Any], value)


def _operation_id(value: object) -> str:
    if not isinstance(value, str) or _OPERATION_ID.fullmatch(value) is None:
        raise ManagedClientError("input_rejected")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ManagedClientError("input_rejected")
        result[key] = value
    return result


def _decode_json(body: bytes) -> object:
    if not body or len(body) > MAX_JSON_REQUEST_BYTES:
        raise ManagedClientError("input_rejected")
    try:
        return json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _item: (_ for _ in ()).throw(
                ManagedClientError("input_rejected")
            ),
        )
    except ManagedClientError:
        raise
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ) as exc:
        raise ManagedClientError("input_rejected") from exc


def _json_response(
    value: object,
    *,
    status: int = HTTPStatus.OK,
    transient: bool = False,
) -> ClientResponse:
    if not transient:
        validate_public_output(value)
    return ClientResponse(
        status=int(status),
        content_type="application/json; charset=utf-8",
        body=json.dumps(value, sort_keys=True, separators=(",", ":")).encode(),
        transient_secret_path=transient,
    )


def _asset(name: str, content_type: str) -> ClientResponse:
    path = ASSET_ROOT / name
    try:
        if path.is_symlink() or not path.is_file():
            raise ManagedClientError("route_rejected")
        body = path.read_bytes()
    except OSError as exc:
        raise ManagedClientError("route_rejected") from exc
    if not body or len(body) > MAX_ASSET_BYTES:
        raise ManagedClientError("route_rejected")
    return ClientResponse(HTTPStatus.OK, content_type, body)


def public_failure(error: BaseException) -> dict[str, object]:
    category = (
        error.category
        if isinstance(error, (ManagedClientError, ClientApiError))
        else "operation_rejected"
    )
    value: dict[str, object] = {
        "api_version": MANAGED_CLIENT_API_VERSION,
        "category": category,
        "status": "rejected",
    }
    validate_public_output(value)
    return value


class ManagedClientApi:
    """One volatile device/account session over the unchanged protocol engine."""

    def __init__(
        self,
        *,
        protocol: Any,
        client_id: str,
        lifecycle_token: str,
        destroy_callback: Callable[[str, str, str], dict[str, Any]],
    ) -> None:
        if _CLIENT_ID.fullmatch(client_id) is None:
            raise ManagedClientError("invalid_client_configuration")
        if (
            not isinstance(lifecycle_token, str)
            or len(lifecycle_token) != 64
            or any(character not in "0123456789abcdef" for character in lifecycle_token)
        ):
            raise ManagedClientError("invalid_client_configuration")
        self.protocol = protocol
        self.client_id = client_id
        self.lifecycle_token = lifecycle_token
        self.destroy_callback = destroy_callback
        self._key: bytearray | None = None
        self._exports: dict[str, bytes] = {}
        self._imported: AuthenticatedRecoveryPackage | None = None
        self._operations: set[str] = set()
        self._self_destroy_results: dict[str, dict[str, object] | None] = {}
        self._self_destroy_status = "ready"
        self._lock = threading.RLock()

    def _replace_key(self, value: bytes | None) -> None:
        prior = self._key
        self._key = None if value is None else bytearray(value)
        if prior is not None:
            for index in range(len(prior)):
                prior[index] = 0

    @contextmanager
    def _performance_observation(self) -> Iterator[None]:
        begin = getattr(self.protocol, "begin_performance_observation", None)
        finish = getattr(self.protocol, "finish_performance_observation", None)
        active = callable(begin) and callable(finish)
        if active:
            cast(Callable[[], object], begin)()
        try:
            yield
        finally:
            if active:
                cast(Callable[[], object], finish)()

    def performance_observation(self, request: object) -> dict[str, object]:
        parsed = _exact(
            request,
            {"api_version", "instrumentation_id"},
            "input_rejected",
        )
        if (
            parsed["api_version"] != MANAGED_CLIENT_API_VERSION
            or parsed["instrumentation_id"] not in PERFORMANCE_INSTRUMENTATION_IDS
            or os.environ.get("LOCUS_PERFORMANCE_EVIDENCE") != "1"
        ):
            raise ManagedClientError("input_rejected")
        value = self.protocol.consume_performance_observation()
        result = {
            "api_version": MANAGED_CLIENT_API_VERSION,
            "instrumentation_id": parsed["instrumentation_id"],
            "observation": value,
            "status": "observed",
        }
        validate_public_output(result)
        return result

    def clear(self) -> None:
        with self._lock:
            self._replace_key(None)
            self._exports.clear()
            self._imported = None
            self._operations.clear()
            self._self_destroy_results.clear()
            self._self_destroy_status = "ready"

    def _use_operation(self, value: object) -> str:
        operation = _operation_id(value)
        if operation in self._operations:
            raise ManagedClientError("operation_conflict")
        if len(self._operations) >= MAX_CLIENT_OPERATIONS:
            raise ManagedClientError("operation_limit_reached")
        self._operations.add(operation)
        return operation

    @property
    def proof_key_thumbprint(self) -> str:
        return client_key_thumbprint(_raw_public(self.protocol.proof_key))

    @property
    def client_identity(self) -> str:
        return hashlib.sha256(
            encode(
                {
                    "client_id": self.client_id,
                    "profile": MANAGED_CLIENT_INSTANCE_PROFILE,
                    "proof_key_thumbprint": self.proof_key_thumbprint,
                }
            )
        ).hexdigest()

    def client_status(self) -> dict[str, object]:
        with self._lock:
            value: dict[str, object] = {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "client_id": self.client_id,
                "client_identity": self.client_identity,
                "client_identity_profile": MANAGED_CLIENT_INSTANCE_PROFILE,
                "key_loaded": self._key is not None,
                "proof_key_thumbprint": self.proof_key_thumbprint,
                "public_fingerprint": (
                    None if self._key is None else _fingerprint(bytes(self._key))
                ),
                "self_destroy_status": self._self_destroy_status,
                "status": "ready",
                "ui_profile": MANAGED_CLIENT_UI_PROFILE,
            }
            validate_public_output(value)
            return value

    def catalog(self) -> dict[str, object]:
        source = self.protocol.catalog()
        value: dict[str, object] = {
            "api_version": MANAGED_CLIENT_API_VERSION,
            "authorization_quorum": 4,
            "policies": source["policies"],
            "profiles": source["profiles"],
            "status": "ready",
            "suites": source["suites"],
        }
        validate_public_output(value)
        return value

    def preview_policy(self, request: object) -> dict[str, object]:
        parsed = _exact(
            request,
            {"api_version", "policy_id", "recovery_input"},
            "input_rejected",
        )
        if parsed["api_version"] != MANAGED_CLIENT_API_VERSION:
            raise ManagedClientError("input_rejected")
        with self._performance_observation():
            result = self.protocol.preview_policy(
                {
                    "api_version": CLIENT_API_VERSION,
                    "policy_id": parsed["policy_id"],
                    "recovery_input": parsed["recovery_input"],
                }
            )
        return {
            "api_version": MANAGED_CLIENT_API_VERSION,
            "normalized_preview": result["normalized_preview"],
            "policy_id": result["policy_id"],
            "status": result["status"],
        }

    def generate_key(self, request: object) -> dict[str, object]:
        parsed = _exact(request, {"api_version", "operation_id"}, "input_rejected")
        if parsed["api_version"] != MANAGED_CLIENT_API_VERSION:
            raise ManagedClientError("input_rejected")
        with self._lock:
            self._use_operation(parsed["operation_id"])
            fixture_id = os.environ.get("LOCUS_PERFORMANCE_FIXTURE_ID")
            if os.environ.get("LOCUS_PERFORMANCE_EVIDENCE") == "1" and fixture_id:
                self._replace_key(
                    hashlib.sha256(
                        b"LOCUS/managed-performance-synthetic-key/v1\x00"
                        + fixture_id.encode("ascii")
                    ).digest()
                )
            else:
                self._replace_key(random_bytes(32))
            assert self._key is not None
            return {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "client_id": self.client_id,
                "private_key": bytes(self._key).hex(),
                "public_fingerprint": _fingerprint(bytes(self._key)),
                "status": "key_generated",
            }

    def reveal_key(self, request: object) -> dict[str, object]:
        parsed = _exact(request, {"api_version"}, "input_rejected")
        if parsed["api_version"] != MANAGED_CLIENT_API_VERSION:
            raise ManagedClientError("input_rejected")
        with self._lock:
            if self._key is None:
                raise ManagedClientError("key_unavailable")
            return {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "client_id": self.client_id,
                "private_key": bytes(self._key).hex(),
                "public_fingerprint": _fingerprint(bytes(self._key)),
                "status": "key_revealed",
            }

    def enroll(self, request: object) -> dict[str, object]:
        parsed = _exact(
            request,
            {
                "api_version",
                "deployment_profile_id",
                "operation_id",
                "policy_id",
                "recovery_input",
                "suite_id",
            },
            "input_rejected",
        )
        if parsed["api_version"] != MANAGED_CLIENT_API_VERSION:
            raise ManagedClientError("input_rejected")
        with self._lock:
            if self._key is None:
                raise ManagedClientError("key_unavailable")
            if len(self._exports) >= MAX_RECOVERY_EXPORTS:
                raise ManagedClientError("package_export_limit_reached")
            operation = self._use_operation(parsed["operation_id"])
            with self._performance_observation():
                result = self.protocol.enroll(
                    {
                        "api_version": CLIENT_API_VERSION,
                        "deployment_profile_id": parsed["deployment_profile_id"],
                        "operation_id": operation,
                        "policy_id": parsed["policy_id"],
                        "protected_key": {
                            "hex": bytes(self._key).hex(),
                            "mode": "import-synthetic",
                        },
                        "recovery_input": parsed["recovery_input"],
                        "suite_id": parsed["suite_id"],
                    }
                )
                public = result.public_value()
                if not secrets.compare_digest(
                    result.public_fingerprint, _fingerprint(bytes(self._key))
                ):
                    raise ManagedClientError("enrollment_rejected")
                package = self.protocol.export_recovery_package(public["receipt"])
            download_id = secrets.token_urlsafe(24)
            self._exports[download_id] = package
            value: dict[str, object] = {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "backup_id": result.backup_id,
                "completed_phases": list(result.completed_phases),
                "deployment_profile_id": parsed["deployment_profile_id"],
                "download_id": download_id,
                "epoch": result.epoch,
                "package_format": RECOVERY_PACKAGE_VERSION,
                "policy_id": result.policy_id,
                "suite_profile_id": result.profile_id,
                "public_fingerprint": result.public_fingerprint,
                "status": "enrolled",
                "suite_id": result.suite_id,
                "threshold": {"k": result.threshold_k, "n": result.threshold_n},
            }
            validate_public_output(value)
            return value

    def exported_package(self, request: object) -> bytes:
        parsed = _exact(
            request, {"api_version", "download_id"}, "package_export_rejected"
        )
        if parsed["api_version"] != MANAGED_CLIENT_API_VERSION or not isinstance(
            parsed["download_id"], str
        ):
            raise ManagedClientError("package_export_rejected")
        with self._lock:
            with self._performance_observation():
                package = self._exports.get(parsed["download_id"])
                if package is None:
                    raise ManagedClientError("package_export_rejected")
                return package

    def import_package(self, encoded: bytes) -> dict[str, object]:
        with self._lock:
            self._imported = None
            with self._performance_observation():
                try:
                    imported = self.protocol.authenticate_recovery_package(encoded)
                except Exception:
                    raise ManagedClientError("package_import_rejected") from None
            self._imported = imported
            bootstrap = imported.bootstrap
            value: dict[str, object] = {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "authorization_quorum": bootstrap.authorization_quorum,
                "backup_id": bootstrap.backup_id,
                "epoch": bootstrap.epoch,
                "holder_ids": list(imported.holder_ids),
                "package_sha256": imported.package_sha256,
                "policy_id": bootstrap.policy_id,
                "deployment_profile_id": imported.deployment_profile_id,
                "public_fingerprint": bootstrap.public_fingerprint,
                "status": "package_authenticated",
                "suite_id": bootstrap.suite_id,
                "suite_profile_id": bootstrap.profile_id,
                "threshold": {
                    "k": bootstrap.threshold_k,
                    "n": bootstrap.threshold_n,
                },
            }
            validate_public_output(value)
            return value

    def recover(self, request: object) -> dict[str, object]:
        parsed = _exact(
            request,
            {
                "api_version",
                "operation_id",
                "recovery_input",
                "selected_holder_ids",
            },
            "recovery_rejected",
        )
        if parsed["api_version"] != MANAGED_CLIENT_API_VERSION:
            raise ManagedClientError("recovery_rejected")
        with self._lock:
            imported = self._imported
            if imported is None:
                raise ManagedClientError("package_required")
            selected_raw = parsed["selected_holder_ids"]
            if not isinstance(selected_raw, list) or any(
                isinstance(item, bool) or not isinstance(item, int)
                for item in selected_raw
            ):
                raise ManagedClientError("recovery_rejected")
            selected = tuple(selected_raw)
            expected_k = imported.bootstrap.threshold_k
            holder_count_valid = (
                1 <= len(selected) <= expected_k
                if os.environ.get("LOCUS_PERFORMANCE_EVIDENCE") == "1"
                else len(selected) == expected_k
            )
            if (
                list(selected) != sorted(set(selected))
                or not holder_count_valid
                or not set(selected) <= set(imported.holder_ids)
            ):
                raise ManagedClientError("recovery_rejected")
            operation = self._use_operation(parsed["operation_id"])
            prior_fingerprint = (
                None if self._key is None else _fingerprint(bytes(self._key))
            )
            with self._performance_observation():
                result = self.protocol.recover(
                    {
                        "api_version": CLIENT_API_VERSION,
                        "operation_id": operation,
                        "receipt": imported.receipt,
                        "recovery_input": parsed["recovery_input"],
                    },
                    selected_holder_ids=selected,
                )
            try:
                recovered_fingerprint = _fingerprint(result.protected_key)
            except (TypeError, ValueError):
                raise ManagedClientError("recovery_rejected") from None
            if not secrets.compare_digest(
                recovered_fingerprint, result.public_fingerprint
            ):
                raise ManagedClientError("recovery_rejected")
            self._replace_key(result.protected_key)
            value: dict[str, object] = {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "backup_id": result.backup_id,
                "completed_phases": list(result.completed_phases),
                "epoch": result.epoch,
                "key_identity_verified": True,
                "key_replaced": True,
                "previous_public_fingerprint": prior_fingerprint,
                "public_fingerprint": result.public_fingerprint,
                "status": "recovered",
                "suite_id": result.suite_id,
            }
            validate_public_output(value)
            return value

    def create_successor(self, request: object) -> dict[str, object]:
        parsed = _exact(
            request,
            {
                "api_version",
                "operation_id",
                "recovery_input",
                "rotate_protected_key",
                "successor_deployment_profile_id",
                "successor_suite_id",
            },
            "successor_rejected",
        )
        if (
            parsed["api_version"] != MANAGED_CLIENT_API_VERSION
            or parsed["rotate_protected_key"] is not False
            or os.environ.get("LOCUS_PERFORMANCE_EVIDENCE") != "1"
        ):
            raise ManagedClientError("successor_rejected")
        with self._lock:
            imported = self._imported
            if imported is None:
                raise ManagedClientError("package_required")
            if len(self._exports) >= MAX_RECOVERY_EXPORTS:
                raise ManagedClientError("package_export_limit_reached")
            operation = self._use_operation(parsed["operation_id"])
            with self._performance_observation():
                started = time.perf_counter_ns()
                result = self.protocol.create_successor(
                    {
                        "api_version": CLIENT_API_VERSION,
                        "operation_id": operation,
                        "receipt": imported.receipt,
                        "recovery_input": parsed["recovery_input"],
                        "rotate_protected_key": False,
                        "successor_deployment_profile_id": parsed[
                            "successor_deployment_profile_id"
                        ],
                        "successor_suite_id": parsed["successor_suite_id"],
                    }
                )
                public = result.enrollment.public_value()
                package = self.protocol.export_recovery_package(public["receipt"])
                successor_import = self.protocol.authenticate_recovery_package(package)
                self.protocol.add_performance_phase(
                    "successor", time.perf_counter_ns() - started
                )
            self._replace_key(result.recovery.protected_key)
            self._imported = successor_import
            download_id = secrets.token_urlsafe(24)
            self._exports[download_id] = package
            value = result.public_value()
            value.update(
                {
                    "api_version": MANAGED_CLIENT_API_VERSION,
                    "deployment_profile_id": successor_import.deployment_profile_id,
                    "download_id": download_id,
                    "package_format": RECOVERY_PACKAGE_VERSION,
                    "suite_profile_id": successor_import.bootstrap.profile_id,
                }
            )
            validate_public_output(value)
            return value

    def self_destroy(self, request: object) -> dict[str, object]:
        parsed = _exact(request, {"api_version", "operation_id"}, "input_rejected")
        if parsed["api_version"] != MANAGED_CLIENT_API_VERSION:
            raise ManagedClientError("input_rejected")
        with self._lock:
            operation = _operation_id(parsed["operation_id"])
            if operation in self._self_destroy_results:
                stored = self._self_destroy_results[operation]
                if stored is not None:
                    return dict(stored)
            else:
                self._use_operation(operation)
                self._self_destroy_results[operation] = None
            try:
                accepted = self.destroy_callback(
                    self.client_id, self.lifecycle_token, operation
                )
            except Exception:
                self._self_destroy_status = "retry_required"
                raise ManagedClientError("self_destroy_rejected") from None
            if (
                not isinstance(accepted, dict)
                or accepted.get("client_id") != self.client_id
                or accepted.get("operation_id") != operation
                or accepted.get("status") != "destroying"
            ):
                self._self_destroy_status = "retry_required"
                raise ManagedClientError("self_destroy_rejected")
            self._replace_key(None)
            self._exports.clear()
            self._imported = None
            self._self_destroy_status = "destroying"
            result: dict[str, object] = {
                "api_version": MANAGED_CLIENT_API_VERSION,
                "client_id": self.client_id,
                "operation_id": operation,
                "self_destroy_status": "destroying",
                "status": "destroying",
            }
            self._self_destroy_results[operation] = dict(result)
            validate_public_output(result)
            return result


class ManagedClientApplication:
    """Strict same-origin route adapter for one managed client instance."""

    def __init__(self, api: ManagedClientApi) -> None:
        self.api = api
        self.csrf_token = secrets.token_urlsafe(32)

    def dispatch(
        self,
        method: str,
        target: str,
        body: bytes = b"",
        *,
        content_type: str | None = None,
        csrf_token: str | None = None,
        origin: str | None = None,
        expected_origin: str = "http://127.0.0.1",
    ) -> ClientResponse:
        parsed_target = urlsplit(target)
        if parsed_target.query or parsed_target.fragment:
            return _json_response(
                {"category": "route_rejected", "status": "rejected"},
                status=HTTPStatus.NOT_FOUND,
            )
        path = parsed_target.path
        try:
            if method == "GET" and path == "/healthz":
                return _json_response({"status": "ok"})
            if method == "GET" and path == "/":
                return _asset("index.html", "text/html; charset=utf-8")
            if method == "GET" and path == "/assets/client.css":
                return _asset("client.css", "text/css; charset=utf-8")
            if method == "GET" and path == "/assets/client.js":
                return _asset("client.js", "text/javascript; charset=utf-8")
            if method == "GET" and path == "/api/v2/session":
                value = self.api.client_status()
                value["csrf_token"] = self.csrf_token
                return _json_response(value)
            if method == "GET" and path == "/api/v2/catalog":
                return _json_response(self.api.catalog())
            if method != "POST" or not path.startswith("/api/v2/"):
                return _json_response(
                    {"category": "route_rejected", "status": "rejected"},
                    status=HTTPStatus.NOT_FOUND,
                )
            if (
                origin != expected_origin
                or not isinstance(csrf_token, str)
                or not secrets.compare_digest(csrf_token, self.csrf_token)
            ):
                raise ManagedClientError("request_authentication_rejected")
            if path == "/api/v2/package/import":
                if content_type != RECOVERY_PACKAGE_MEDIA_TYPE:
                    raise ManagedClientError("package_import_rejected")
                return _json_response(self.api.import_package(body))
            if content_type != "application/json":
                raise ManagedClientError("input_rejected")
            request = _decode_json(body)
            if path == "/api/v2/preview-policy":
                return _json_response(self.api.preview_policy(request), transient=True)
            if path == "/api/v2/key/generate":
                return _json_response(self.api.generate_key(request), transient=True)
            if path == "/api/v2/key/reveal":
                return _json_response(self.api.reveal_key(request), transient=True)
            if path == "/api/v2/enroll":
                return _json_response(self.api.enroll(request))
            if path == "/api/v2/performance-observation":
                return _json_response(self.api.performance_observation(request))
            if path == "/api/v2/package/export":
                package = self.api.exported_package(request)
                return ClientResponse(
                    HTTPStatus.OK,
                    RECOVERY_PACKAGE_MEDIA_TYPE,
                    package,
                    content_disposition=(
                        'attachment; filename="locus-encrypted-recovery-package.locus"'
                    ),
                )
            if path == "/api/v2/recover":
                return _json_response(self.api.recover(request))
            if path == "/api/v2/successor":
                return _json_response(self.api.create_successor(request))
            if path == "/api/v2/self-destroy":
                return _json_response(
                    self.api.self_destroy(request), status=HTTPStatus.ACCEPTED
                )
            return _json_response(
                {"category": "route_rejected", "status": "rejected"},
                status=HTTPStatus.NOT_FOUND,
            )
        except Exception as exc:
            failure = public_failure(exc)
            status = (
                HTTPStatus.CONFLICT
                if failure["category"] == "operation_conflict"
                else HTTPStatus.BAD_REQUEST
            )
            return _json_response(failure, status=status)


SECURITY_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Content-Security-Policy": (
        "default-src 'none'; base-uri 'none'; connect-src 'self'; "
        "form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; "
        "object-src 'none'; script-src 'self'; style-src 'self'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": (
        "camera=(), clipboard-read=(), clipboard-write=(), geolocation=(), "
        "microphone=(), payment=(), usb=()"
    ),
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


class ManagedClientServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, address: tuple[str, int], application: ManagedClientApplication
    ) -> None:
        self.application = application
        super().__init__(address, ManagedClientRequestHandler)

    def handle_error(self, request: object, client_address: object) -> None:
        del request, client_address


class ManagedClientRequestHandler(BaseHTTPRequestHandler):
    server: ManagedClientServer
    server_version = "LOCUSManagedClientUI/1"
    sys_version = ""

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._handle("POST")

    def _handle(self, method: str) -> None:
        body = b""
        content_type = None
        if method == "POST":
            maximum = (
                MAX_RECOVERY_PACKAGE_BYTES
                if urlsplit(self.path).path == "/api/v2/package/import"
                else MAX_JSON_REQUEST_BYTES
            )
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                length = -1
            if length < 1 or length > maximum:
                self._send(
                    _json_response(
                        {
                            "api_version": MANAGED_CLIENT_API_VERSION,
                            "category": "input_rejected",
                            "status": "rejected",
                        },
                        status=HTTPStatus.BAD_REQUEST,
                    )
                )
                return
            body = self.rfile.read(length)
            content_type = self.headers.get("Content-Type")
        context = self.headers.get(FLOW_HEADER) if flow_enabled() else None
        path = urlsplit(self.path).path
        category = http_category("managed-client", self.path) if context else ""
        with flow_context(context):
            try:
                if method == "GET" and path == "/healthz":
                    response = self.server.application.dispatch(method, self.path)
                else:
                    expected_origin = _loopback_origin(self.headers.get("Host", ""))
                    response = self.server.application.dispatch(
                        method,
                        self.path,
                        body,
                        content_type=content_type,
                        csrf_token=self.headers.get("X-LOCUS-CSRF"),
                        origin=self.headers.get("Origin"),
                        expected_origin=expected_origin,
                    )
            except Exception:
                response = _json_response(
                    {
                        "api_version": MANAGED_CLIENT_API_VERSION,
                        "category": "request_authentication_rejected",
                        "status": "rejected",
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
            if category:
                emit_flow(
                    sender="browser",
                    receiver="managed-client",
                    category=category,
                    request_bytes=len(body),
                    response_bytes=len(response.body),
                    result=flow_outcome(response.status),
                    observation="receiver",
                )
        self._send(response)

    def _send(self, response: ClientResponse) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        if response.content_type.startswith("text/html"):
            self.send_header("Clear-Site-Data", '"cache", "cookies", "storage"')
        if response.transient_secret_path:
            self.send_header("X-LOCUS-Transient", "active-client-only")
        if response.content_disposition is not None:
            self.send_header("Content-Disposition", response.content_disposition)
        self.end_headers()
        self.wfile.write(response.body)


def _destroy_callback(
    root: Path, endpoint: str
) -> Callable[[str, str, str], dict[str, Any]]:
    def destroy(client_id: str, token: str, operation_id: str) -> dict[str, Any]:
        return rpc_request(
            endpoint=endpoint,
            path="/v1/client/self-destroy",
            role_root=root,
            value={
                "client_id": client_id,
                "operation_id": operation_id,
                "token": token,
            },
        )

    return destroy


def _loopback_origin(host_header: str) -> str:
    """Return the local browser origin represented by a safe Host header."""

    try:
        parsed = urlsplit(f"http://{host_header}")
        if (
            parsed.scheme != "http"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.hostname is None
            or parsed.port is None
        ):
            raise ValueError
        if (
            parsed.hostname != "localhost"
            and not ipaddress.ip_address(parsed.hostname).is_loopback
        ):
            raise ValueError
    except ValueError as exc:
        raise ManagedClientError("request_authentication_rejected") from exc
    return f"http://{host_header}"


def browser_edge_bind_address(gateway: str | None = None) -> str:
    """Return the address on the controller-validated browser-edge network."""

    try:
        gateway_address = ipaddress.ip_address(
            gateway if gateway is not None else os.environ["LOCUS_BROWSER_EDGE_GATEWAY"]
        )
        if (
            not isinstance(gateway_address, ipaddress.IPv4Address)
            or gateway_address.is_loopback
            or gateway_address.is_unspecified
            or gateway_address.is_multicast
        ):
            raise ValueError
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect((str(gateway_address), 9))
            address = str(probe.getsockname()[0])
        parsed = ipaddress.ip_address(address)
    except (KeyError, OSError, ValueError) as exc:
        raise ManagedClientError("browser_edge_binding_rejected") from exc
    if (
        parsed.is_loopback
        or parsed.is_unspecified
        or not isinstance(parsed, ipaddress.IPv4Address)
    ):
        raise ManagedClientError("browser_edge_binding_rejected")
    return address


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    configure_role("managed-client")
    client_id = os.environ["LOCUS_CLIENT_INSTANCE_ID"]
    lifecycle_token = os.environ["LOCUS_CLIENT_SELF_DESTRUCT_TOKEN"]
    controller = os.environ["LOCUS_MANAGER_CONTROL_ENDPOINT"]
    protocol = IntegratedResearchClientApi(
        role_root=args.root,
        proof_key=Ed25519PrivateKey.generate(),
        deployment_id="LOCUS-integrated-manager-deployment-v1",
    )
    api = ManagedClientApi(
        protocol=protocol,
        client_id=client_id,
        lifecycle_token=lifecycle_token,
        destroy_callback=_destroy_callback(args.root, controller),
    )
    application = ManagedClientApplication(api)
    bind_address = browser_edge_bind_address()
    with ManagedClientServer((bind_address, args.port), application) as server:
        print(
            json.dumps(
                {
                    "backend": "integrated-services",
                    "bind_address": bind_address,
                    "client_id": client_id,
                    "status": "ready",
                    "ui_profile": MANAGED_CLIENT_UI_PROFILE,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )
        server.serve_forever(poll_interval=0.2)


if __name__ == "__main__":
    main()


__all__ = [
    "ASSET_ROOT",
    "MANAGED_CLIENT_API_VERSION",
    "MANAGED_CLIENT_INSTANCE_PROFILE",
    "MANAGED_CLIENT_UI_PROFILE",
    "RECOVERY_PACKAGE_MEDIA_TYPE",
    "ClientResponse",
    "ManagedClientApi",
    "ManagedClientApplication",
    "ManagedClientError",
    "ManagedClientServer",
    "SECURITY_HEADERS",
    "browser_edge_bind_address",
]
