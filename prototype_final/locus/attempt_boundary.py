"""Bind the frozen attempt counterexample to the managed deployment boundary."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .attempt_model import build_model_report, validate_model_report
from .managed_manifest import (
    MANAGED_CONFIG_VERSION,
    MANAGED_DEPLOYMENT_ID,
    load_managed_manifest,
)

MODEL_SOURCE_SHA256 = "4f118eaf019abf6c02779b891146fa6a2bcafe6175927e1c2587632195955b2c"
MODEL_SCHEMA_SHA256 = "80f0e87bb523dcd2a282313f9161a1866fadbd2d148063045714765b70fdc428"
CERTIFICATE_SOURCE_SHA256 = (
    "b280e14b331850041bdd61643fda369116b6e12af6331df00b5207563754f402"
)


class AttemptBoundaryError(ValueError):
    """The managed deployment no longer matches the frozen boundary."""


def _normalized_sha256(path: Path) -> str:
    data = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def validate_managed_attempt_boundary(manifest: object) -> dict[str, Any]:
    """Require the exact D025 quorum and absence of a monotonic-witness role."""

    if not isinstance(manifest, dict):
        raise AttemptBoundaryError("invalid managed attempt boundary")
    if (
        manifest.get("version") != MANAGED_CONFIG_VERSION
        or manifest.get("deployment_id") != MANAGED_DEPLOYMENT_ID
        or manifest.get("authorization")
        != {"authorizers": [1, 2, 3, 4, 5], "quorum": 4}
    ):
        raise AttemptBoundaryError("managed authorization boundary changed")
    services = manifest.get("services")
    if not isinstance(services, list):
        raise AttemptBoundaryError("invalid managed service inventory")
    names = [item.get("name") for item in services if isinstance(item, dict)]
    if len(names) != len(services) or any(
        "witness" in str(name) or "monotonic" in str(name) for name in names
    ):
        raise AttemptBoundaryError("managed monotonic-witness boundary changed")
    return manifest


def build_integrated_attempt_boundary_report(root: Path) -> dict[str, object]:
    """Validate the managed binding, then run the unchanged frozen model."""

    model_path = root / "locus" / "attempt_model.py"
    certificate_path = root / "locus" / "attempt_certificates.py"
    schema_path = root / "docs" / "schemas" / "attempt-model-report-v1.schema.json"
    if _normalized_sha256(model_path) != MODEL_SOURCE_SHA256:
        raise AttemptBoundaryError("frozen attempt model changed")
    if _normalized_sha256(schema_path) != MODEL_SCHEMA_SHA256:
        raise AttemptBoundaryError("frozen attempt model schema changed")
    if _normalized_sha256(certificate_path) != CERTIFICATE_SOURCE_SHA256:
        raise AttemptBoundaryError("frozen attempt certificate implementation changed")
    manifest = load_managed_manifest(root / "deploy" / "managed-manifest.json")
    validate_managed_attempt_boundary(manifest)
    return validate_model_report(build_model_report())


__all__ = [
    "CERTIFICATE_SOURCE_SHA256",
    "MODEL_SCHEMA_SHA256",
    "MODEL_SOURCE_SHA256",
    "AttemptBoundaryError",
    "build_integrated_attempt_boundary_report",
    "validate_managed_attempt_boundary",
]
