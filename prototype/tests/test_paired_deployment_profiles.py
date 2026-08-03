from __future__ import annotations

import json
import unittest

from locus.appss_formats import (
    APPSS_PROFILE_2_OF_3,
    APPSS_PROFILE_3_OF_5,
    APPSS_SUITE_ID,
    RECOVERY_SUITE_SELECTOR,
    RECOVERY_SUITE_SELECTOR_V2,
    YI_PROFILE_2_OF_3,
    YI_PROFILE_3_OF_5,
    YI_SUITE_ID,
)
from locus.paired_deployment_profiles import PAIRED_PROFILES, paired_profile
from locus.recovery_suite_registry import RecoverySuiteRegistry


class PairedDeploymentProfileTests(unittest.TestCase):
    def test_both_topologies_freeze_matching_comparison_controls(self) -> None:
        registry = RecoverySuiteRegistry()
        expected = {
            (2, 3): {
                YI_SUITE_ID: YI_PROFILE_2_OF_3,
                APPSS_SUITE_ID: APPSS_PROFILE_2_OF_3,
            },
            (3, 5): {
                YI_SUITE_ID: YI_PROFILE_3_OF_5,
                APPSS_SUITE_ID: APPSS_PROFILE_3_OF_5,
            },
        }
        for profile in PAIRED_PROFILES.values():
            topology = (profile.threshold.k, profile.threshold.n)
            self.assertEqual(profile.authorizer_ids, (1, 2, 3, 4, 5))
            self.assertEqual(profile.authorization_quorum, 4)
            for suite_id in (YI_SUITE_ID, APPSS_SUITE_ID):
                encoded = profile.selector_for(suite_id)
                decoded = json.loads(encoded)
                expected_version = (
                    RECOVERY_SUITE_SELECTOR
                    if topology == (2, 3)
                    else RECOVERY_SUITE_SELECTOR_V2
                )
                self.assertEqual(decoded["version"], expected_version)
                selection, _adapter = registry.select_new_epoch(encoded)
                profile.validate_selection(selection)
                self.assertEqual(selection.profile_id, expected[topology][suite_id])

    def test_unknown_profile_and_cross_topology_selection_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            paired_profile("test-only:unknown-deployment")
        profiles = tuple(PAIRED_PROFILES.values())
        registry = RecoverySuiteRegistry()
        selection, _adapter = registry.select_new_epoch(
            profiles[0].selector_for(YI_SUITE_ID)
        )
        with self.assertRaises(ValueError):
            profiles[1].validate_selection(selection)


if __name__ == "__main__":
    unittest.main()
