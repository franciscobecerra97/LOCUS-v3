from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs/version-registry-v1.json"
SCHEMA_PATH = ROOT / "docs/schemas/version-registry-v1.schema.json"
IDENTIFIER_PATTERN = re.compile(r"LOCUS-[A-Za-z0-9_-]+-v[0-9]+")
DECISION_PATTERN = re.compile(r"D[0-9]{3}")
PHASE_PATTERN = re.compile(r"P[0-9]+(?:A)?(?:\.[0-9]+)?")
FAMILY_PATTERN = re.compile(r"[a-z][a-z0-9-]*")

FROZEN_MINIMUM = {
    "LOCUS-location-person-set-v1",
    "LOCUS-location-person-pair-v1",
    "LOCUS-reference-backup-v4",
    "LOCUS-cloud-backup-object-v1",
    "LOCUS-cloud-backup-reference-v1",
    "LOCUS-compose-deployment-v2",
    "LOCUS-TPASS-YI-ZK-RISTRETTO255-v1",
    "LOCUS-attempt-config-v2",
    "LOCUS-anonymous-artifact-v1",
    "LOCUS-anonymous-artifact-v2",
}
REQUIRED_RESERVATIONS = {
    "admission",
    "artifact",
    "backup-and-bundle",
    "deployment",
    "descriptor",
    "policy-and-resolver",
    "recovery-suite",
    "result",
    "trace",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} is not a JSON object")
    return value


def active_text_paths() -> list[Path]:
    paths = [
        *ROOT.glob("*.md"),
        *ROOT.glob("*.json"),
        ROOT / "tasks.py",
        *(ROOT / "deploy").rglob("*"),
        *(ROOT / "prototype").rglob("*.py"),
        *(ROOT / "prototype").rglob("*.json"),
        *(ROOT / "prototype").rglob("*.txt"),
        *(ROOT / "docs").rglob("*.md"),
        *(ROOT / "docs/schemas").rglob("*.json"),
        *(ROOT / "artifact").rglob("*.md"),
        *(ROOT / "artifact").rglob("*.json"),
        *(ROOT / "appss-core/src").rglob("*.rs"),
        *(ROOT / "appss-core/tests").rglob("*.rs"),
        *(ROOT / "appss-core/test-vectors").rglob("*.txt"),
        *(ROOT / "tpass-core/src").rglob("*.rs"),
        *(ROOT / "tpass-core/test-vectors").rglob("*.txt"),
        *(ROOT / "tpass-python/src").rglob("*.rs"),
    ]
    return sorted(
        {
            path
            for path in paths
            if "upstream-baseline" not in path.parts
            and path != REGISTRY_PATH
            and path.is_file()
        }
    )


class VersionRegistryTests(unittest.TestCase):
    def test_registry_and_schema_have_exact_public_shape(self) -> None:
        registry = load_json(REGISTRY_PATH)
        schema = load_json(SCHEMA_PATH)
        self.assertEqual(
            set(registry),
            {"artifact", "namespace", "protected_identifiers", "reservations"},
        )
        self.assertEqual(registry["artifact"], "LOCUS-version-registry-v1")
        self.assertEqual(registry["namespace"], "LOCUS")
        self.assertEqual(
            schema["properties"]["artifact"]["const"], registry["artifact"]
        )
        self.assertEqual(schema["properties"]["namespace"]["const"], "LOCUS")
        self.assertFalse(schema["additionalProperties"])
        reservation_schema = schema["properties"]["reservations"]["items"]
        self.assertFalse(reservation_schema["additionalProperties"])
        self.assertNotIn("identifier", reservation_schema["properties"])

    def test_protected_identifiers_are_canonical_and_collision_free(self) -> None:
        identifiers = load_json(REGISTRY_PATH)["protected_identifiers"]
        self.assertIsInstance(identifiers, list)
        self.assertEqual(identifiers, sorted(identifiers, key=str.casefold))
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(
            len(identifiers), len({item.casefold() for item in identifiers})
        )
        for identifier in identifiers:
            self.assertIsInstance(identifier, str)
            self.assertIsNotNone(IDENTIFIER_PATTERN.fullmatch(identifier))
        self.assertTrue(FROZEN_MINIMUM.issubset(identifiers))

    def test_every_active_identifier_is_in_the_protected_ledger(self) -> None:
        protected = set(load_json(REGISTRY_PATH)["protected_identifiers"])
        observed: set[str] = set()
        for path in active_text_paths():
            observed.update(
                IDENTIFIER_PATTERN.findall(path.read_text(encoding="utf-8"))
            )
        self.assertEqual(observed - protected, set())

    def test_future_families_are_reserved_without_premature_identifiers(self) -> None:
        reservations = load_json(REGISTRY_PATH)["reservations"]
        self.assertIsInstance(reservations, list)
        families = [item["family"] for item in reservations]
        self.assertEqual(families, sorted(families))
        self.assertEqual(set(families), REQUIRED_RESERVATIONS)
        self.assertEqual(len(families), len(set(families)))
        for reservation in reservations:
            self.assertEqual(
                set(reservation),
                {
                    "family",
                    "allocation_phase",
                    "decisions",
                    "required_gate",
                    "compatibility_rule",
                },
            )
            self.assertIsNotNone(FAMILY_PATTERN.fullmatch(reservation["family"]))
            self.assertIsNotNone(
                PHASE_PATTERN.fullmatch(reservation["allocation_phase"])
            )
            self.assertEqual(
                reservation["decisions"], sorted(set(reservation["decisions"]))
            )
            self.assertTrue(reservation["decisions"])
            for decision in reservation["decisions"]:
                self.assertIsNotNone(DECISION_PATTERN.fullmatch(decision))
            self.assertTrue(reservation["required_gate"].strip())
            self.assertTrue(reservation["compatibility_rule"].strip())


if __name__ == "__main__":
    unittest.main()
