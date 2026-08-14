from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "p8.1-decoder-transition-inventory.json"
SCHEMA = ROOT / "docs" / "schemas" / "p8.1-decoder-transition-inventory.schema.json"
ROUTE_SOURCES = (
    "locus/integrated_services.py",
    "locus/integrated_manager.py",
    "locus/integrated_controller.py",
    "locus/managed_client_ui.py",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise AssertionError(f"non-object JSON: {path}")
    return value


def _route_literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    prefixes = ("/api/", "/assets/", "/health", "/v1/")
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and (node.value == "/" or node.value.startswith(prefixes))
        and "{" not in node.value
        and (node.value == "/" or not node.value.endswith("/"))
    }


class P81AssuranceInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = _load(INVENTORY)

    def test_inventory_and_schema_are_bounded_governance_artifacts(self) -> None:
        schema = _load(SCHEMA)
        self.assertEqual(
            schema["$schema"], "https://json-schema.org/draft/2020-12/schema"
        )
        self.assertEqual(self.inventory["inventory_version"], 1)
        self.assertEqual(self.inventory["scope"], "prototype_final")
        self.assertEqual(self.inventory["status"], "complete")
        self.assertIs(self.inventory["retained_evidence"], False)
        self.assertEqual(
            set(self.inventory),
            {
                "inventory_version",
                "scope",
                "status",
                "retained_evidence",
                "external_surfaces",
                "durable_transitions",
                "cross_cutting_controls",
            },
        )
        for collection in (
            "external_surfaces",
            "durable_transitions",
            "cross_cutting_controls",
        ):
            values = self.inventory[collection]
            self.assertIsInstance(values, list)
            self.assertTrue(values)
            identifiers = [item["id"] for item in values]
            self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_every_reference_names_an_existing_source_or_test_symbol(self) -> None:
        references: list[str] = []
        for surface in self.inventory["external_surfaces"]:
            source = ROOT / surface["source"]
            self.assertTrue(source.is_file(), source)
            self.assertTrue(surface["decoder"])
            references.extend(surface["negative_tests"])
            references.extend(surface["authenticated_transport_tests"])
        for transition in self.inventory["durable_transitions"]:
            self.assertTrue((ROOT / transition["source"]).is_file())
            self.assertTrue(transition["symbol"])
            references.extend(transition["tests"])
        for control in self.inventory["cross_cutting_controls"]:
            references.extend(control["tests"])
        for reference in references:
            with self.subTest(reference=reference):
                relative, symbol = reference.split("::", 1)
                source = ROOT / relative
                self.assertTrue(source.is_file(), source)
                self.assertIn(symbol, source.read_text(encoding="utf-8"))

    def test_inventory_covers_every_active_external_route_literal(self) -> None:
        source_routes: set[str] = set()
        for source in ROUTE_SOURCES:
            source_routes.update(_route_literals(ROOT / source))
        inventory_routes = {
            route
            for surface in self.inventory["external_surfaces"]
            for route in surface["routes"]
        }
        self.assertEqual(inventory_routes, source_routes)

    def test_each_surface_and_transition_has_negative_or_retry_coverage(self) -> None:
        for surface in self.inventory["external_surfaces"]:
            self.assertTrue(surface["negative_tests"], surface["id"])
            self.assertTrue(surface["authenticated_transport_tests"], surface["id"])
        for transition in self.inventory["durable_transitions"]:
            self.assertTrue(transition["tests"], transition["id"])


if __name__ == "__main__":
    unittest.main()
