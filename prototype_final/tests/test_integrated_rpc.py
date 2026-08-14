from __future__ import annotations

import http.client
import json
import ssl
import tempfile
import unittest
from pathlib import Path
from typing import Any

from locus.codec import encode
from locus.integrated_bootstrap import bootstrap_integrated_roles
from locus.integrated_rpc import (
    MAX_RPC_BYTES,
    IntegratedRpcError,
    RpcServerThread,
    decode_rpc,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "deploy" / "integrated-manifest.json"


class IntegratedRpcTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "roles"
        bootstrap_integrated_roles(root=self.root, manifest_path=MANIFEST)

    def _context(self, role: str, *, certificate: bool = True) -> ssl.SSLContext:
        root = self.root / role
        context = ssl.create_default_context(cafile=str(root / "ca.pem"))
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        context.check_hostname = False
        if certificate:
            context.load_cert_chain(root / "tls-cert.pem", root / "tls-key.pem")
        return context

    @staticmethod
    def _post(
        server: RpcServerThread,
        context: ssl.SSLContext,
        body: bytes,
    ) -> tuple[int, dict[str, Any]]:
        connection = http.client.HTTPSConnection(
            "127.0.0.1", server.port, context=context, timeout=5
        )
        try:
            connection.request(
                "POST",
                "/v1/test",
                body=body,
                headers={
                    "Content-Length": str(len(body)),
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_decoder_rejects_noncanonical_duplicate_oversized_and_nonobjects(
        self,
    ) -> None:
        self.assertEqual(decode_rpc(b'{"a":1}'), {"a": 1})
        rejected = (
            b"",
            b" {}",
            b'{"a":1,"a":2}',
            b"[]",
            b'{"a":NaN}',
            b"\xff",
            b"{" + b"a" * MAX_RPC_BYTES + b"}",
        )
        for encoded in rejected:
            with self.subTest(encoded=encoded[:40]):
                with self.assertRaises(IntegratedRpcError):
                    decode_rpc(encoded)

    def test_live_transport_requires_client_certificate_and_exposes_peer_role(
        self,
    ) -> None:
        observed: list[tuple[str, dict[str, Any], str]] = []

        def handler(
            path: str, request: dict[str, Any], peer: str
        ) -> tuple[int, dict[str, Any]]:
            observed.append((path, request, peer))
            return 200, {"peer": peer, "status": "ok"}

        with RpcServerThread(
            role_root=self.root / "operator", handler=handler
        ) as server:
            status, response = self._post(
                server, self._context("ui-client-a"), encode({"value": 1})
            )
            self.assertEqual(status, 200)
            self.assertEqual(response, {"peer": "ui-client-a", "status": "ok"})
            self.assertEqual(observed, [("/v1/test", {"value": 1}, "ui-client-a")])

            status, response = self._post(
                server,
                self._context("ui-client-a"),
                b'{"value":1,"value":2}',
            )
            self.assertEqual(status, 400)
            self.assertEqual(response["category"], "input_rejected")
            self.assertEqual(len(observed), 1)

            with self.assertRaises((OSError, ssl.SSLError)):
                self._post(
                    server,
                    self._context("ui-client-a", certificate=False),
                    encode({"value": 1}),
                )


if __name__ == "__main__":
    unittest.main()
