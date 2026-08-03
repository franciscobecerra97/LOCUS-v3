from __future__ import annotations

import json
import unittest

from locus.appss import AppssRecoveryAdapter
from locus.appss_formats import APPSS_SUITE_ID, YI_SUITE_ID
from locus.recovery_suite_registry import RecoverySuiteRegistry
from locus.yi_compat import RecoverySuiteError, YiTpassRecoveryAdapter


class RecoverySuiteRegistryTests(unittest.TestCase):
    def test_exact_two_suite_registry_and_explicit_selection(self) -> None:
        registry = RecoverySuiteRegistry()
        self.assertEqual(
            registry.suite_ids, tuple(sorted((APPSS_SUITE_ID, YI_SUITE_ID)))
        )
        for suite_id, expected_type in (
            (YI_SUITE_ID, YiTpassRecoveryAdapter),
            (APPSS_SUITE_ID, AppssRecoveryAdapter),
        ):
            selector = registry.selector_bytes(suite_id=suite_id)
            selection, adapter = registry.select_new_epoch(selector)
            self.assertEqual(selection.suite_id, suite_id)
            self.assertEqual((selection.threshold.k, selection.threshold.n), (2, 3))
            self.assertIsInstance(adapter, expected_type)
            self.assertIs(
                registry.for_authenticated_descriptor(suite_id).__class__, expected_type
            )

    def test_recovery_dispatch_has_no_fallback_or_caller_override(self) -> None:
        registry = RecoverySuiteRegistry()
        with self.assertRaises(RecoverySuiteError):
            registry.for_authenticated_descriptor("test-only:unknown-suite")
        selector = json.loads(registry.selector_bytes(suite_id=APPSS_SUITE_ID))
        selector["fallback_suite_id"] = YI_SUITE_ID
        with self.assertRaises(RecoverySuiteError):
            registry.select_new_epoch(
                json.dumps(selector, sort_keys=True, separators=(",", ":")).encode()
            )
        with self.assertRaises(RecoverySuiteError):
            registry.selector_bytes(suite_id="test-only:unknown-suite")

    def test_suite_profile_pairing_is_fail_closed(self) -> None:
        registry = RecoverySuiteRegistry()
        selector = json.loads(registry.selector_bytes(suite_id=APPSS_SUITE_ID))
        selector["profile_id"] = "LOCUS-TPASS-YI-2of3-v1"
        with self.assertRaises(RecoverySuiteError):
            registry.select_new_epoch(
                json.dumps(selector, sort_keys=True, separators=(",", ":")).encode()
            )


if __name__ == "__main__":
    unittest.main()
