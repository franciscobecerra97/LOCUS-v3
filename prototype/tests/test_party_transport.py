from __future__ import annotations

import hashlib
import json
import ssl
import unittest
from unittest import mock

from locus.party_http import (
    API_VERSION,
    PartyProtocolError,
    PartyUnavailable,
    RemoteAuthorizerNode,
)


class _Socket:
    def __init__(self, certificate: bytes) -> None:
        self.certificate = certificate

    def getpeercert(self, *, binary_form: bool = False) -> bytes | dict[str, object]:
        return self.certificate if binary_form else {}


class _Response:
    def __init__(
        self, *, status: int, body: bytes, content_type: str = "application/json"
    ) -> None:
        self.status = status
        self.body = body
        self.content_type = content_type

    def read(self, limit: int) -> bytes:
        return self.body[:limit]

    def getheader(self, name: str) -> str | None:
        return self.content_type if name == "Content-Type" else None


class _Connection:
    def __init__(
        self,
        *,
        certificate: bytes,
        response: _Response | None = None,
        connect_error: OSError | None = None,
    ) -> None:
        self.sock: _Socket | None = _Socket(certificate)
        self.response = response
        self.connect_error = connect_error
        self.requests: list[tuple[str, str, bytes, dict[str, str]]] = []

    def connect(self) -> None:
        if self.connect_error is not None:
            raise self.connect_error

    def request(
        self, method: str, path: str, *, body: bytes, headers: dict[str, str]
    ) -> None:
        self.requests.append((method, path, body, headers))

    def getresponse(self) -> _Response:
        if self.response is None:
            raise AssertionError("synthetic connection has no response")
        return self.response

    def close(self) -> None:
        return


def _body(*, status: int = 200, code: str | None = None) -> bytes:
    value: dict[str, object]
    if status == 200:
        value = {"api_version": API_VERSION, "party_id": 1, "result": {"ok": True}}
    else:
        value = {
            "api_version": API_VERSION,
            "error": {"code": code},
            "party_id": 1,
        }
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")


def _client(*, certificate: bytes, attempts: int) -> RemoteAuthorizerNode:
    client = object.__new__(RemoteAuthorizerNode)
    client._party_id = 1
    client.host = "party.example"
    client.port = 8443
    client.server_certificate_sha256 = hashlib.sha256(certificate).hexdigest()
    client.client_certificate_sha256 = "11" * 32
    client.timeout_seconds = 0.1
    client.transport_attempts = attempts
    client._request_body_bytes = 0
    client._response_body_bytes = 0
    client._tls = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return client


class PartyTransportPolicyTests(unittest.TestCase):
    def test_transport_retry_reuses_exact_body_and_key(self) -> None:
        certificate = b"synthetic-server-certificate"
        connections = [
            _Connection(
                certificate=certificate,
                connect_error=TimeoutError("synthetic timeout"),
            ),
            _Connection(
                certificate=certificate,
                response=_Response(status=200, body=_body()),
            ),
        ]
        with mock.patch(
            "locus.party_http.http.client.HTTPSConnection",
            side_effect=connections,
        ):
            client = _client(certificate=certificate, attempts=2)
            result = client._post("/v1/test", {"value": 1}, idempotency_key="ab" * 32)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(connections[1].requests), 1)
        _, _, _, headers = connections[1].requests[0]
        self.assertEqual(headers["Idempotency-Key"], "ab" * 32)
        self.assertEqual(
            client.application_bytes,
            {
                "received": len(_body()),
                "sent": len(connections[1].requests[0][2]),
            },
        )

    def test_request_in_progress_is_exactly_retried(self) -> None:
        certificate = b"synthetic-server-certificate"
        connections = [
            _Connection(
                certificate=certificate,
                response=_Response(
                    status=409,
                    body=_body(status=409, code="request_in_progress"),
                ),
            ),
            _Connection(
                certificate=certificate,
                response=_Response(status=200, body=_body()),
            ),
        ]
        with mock.patch(
            "locus.party_http.http.client.HTTPSConnection",
            side_effect=connections,
        ):
            result = _client(certificate=certificate, attempts=2)._post(
                "/v1/test", {"value": 1}, idempotency_key="cd" * 32
            )
        self.assertEqual(result, {"ok": True})
        first = connections[0].requests[0]
        second = connections[1].requests[0]
        self.assertEqual(first[2:], second[2:])

    def test_protocol_fault_is_not_retried(self) -> None:
        certificate = b"synthetic-server-certificate"
        connection = _Connection(
            certificate=certificate,
            response=_Response(status=200, body=_body(), content_type="text/plain"),
        )
        constructor = mock.Mock(return_value=connection)
        with mock.patch("locus.party_http.http.client.HTTPSConnection", constructor):
            with self.assertRaises(PartyProtocolError):
                _client(certificate=certificate, attempts=3)._post(
                    "/v1/test", {"value": 1}, idempotency_key="ef" * 32
                )
        constructor.assert_called_once()

    def test_transport_attempts_are_bounded(self) -> None:
        certificate = b"synthetic-server-certificate"
        constructor = mock.Mock(
            side_effect=[
                _Connection(
                    certificate=certificate,
                    connect_error=TimeoutError("synthetic timeout"),
                ),
                _Connection(
                    certificate=certificate,
                    connect_error=TimeoutError("synthetic timeout"),
                ),
            ]
        )
        with mock.patch("locus.party_http.http.client.HTTPSConnection", constructor):
            with self.assertRaises(PartyUnavailable):
                _client(certificate=certificate, attempts=2)._post(
                    "/v1/test", {"value": 1}, idempotency_key="12" * 32
                )
        self.assertEqual(constructor.call_count, 2)


if __name__ == "__main__":
    unittest.main()
