from __future__ import annotations

import json
import unittest

from locus.redaction import exposed_categories, validate_public_output
from locus.walkthrough import (
    WalkthroughError,
    enroll_walkthrough,
    enrollment_report,
    parse_identifiers,
    recover_walkthrough,
    run_interactive,
)


class WalkthroughTests(unittest.TestCase):
    def test_successful_native_walkthrough_is_redacted(self) -> None:
        enrollment = enroll_walkthrough((1, 2, 3))
        enrollment_summary = enrollment_report(enrollment)
        result = recover_walkthrough(enrollment, (3, 2, 1), (1, 3))
        recovery_summary = result.public_report()

        self.assertTrue(result.success)
        self.assertEqual(result.attempt_number, 1)
        self.assertEqual(enrollment_summary["selected_pairs"], 3)
        self.assertEqual(enrollment_summary["threshold"], 2)
        validate_public_output(enrollment_summary)
        validate_public_output(recovery_summary)

        rendered = json.dumps(
            {"enrollment": enrollment_summary, "recovery": recovery_summary},
            sort_keys=True,
        )
        self.assertNotIn("alpha@example.org", rendered)
        self.assertNotIn(
            enrollment.cloud_backup["ciphertext"]["ciphertext"],
            rendered,
        )
        self.assertNotIn("ciphertext", repr(enrollment))
        for material in enrollment.holder_material:
            self.assertNotIn(bytes(material.to_secret_bytes()).hex(), rendered)
        self.assertEqual(exposed_categories(rendered, {}), [])

    def test_wrong_fictional_selection_is_a_counted_generic_rejection(self) -> None:
        enrollment = enroll_walkthrough((1, 2, 3))
        rejected = recover_walkthrough(enrollment, (1, 2, 4), (1, 2))
        recovered = recover_walkthrough(enrollment, (1, 2, 3), (2, 3))

        self.assertFalse(rejected.success)
        self.assertEqual(rejected.public_report()["outcome"], "generic-rejection")
        self.assertEqual(rejected.attempt_number, 1)
        self.assertTrue(recovered.success)
        self.assertEqual(recovered.attempt_number, 2)

    def test_attempt_budget_fails_closed(self) -> None:
        enrollment = enroll_walkthrough((1, 2, 3))
        enrollment.attempts = enrollment.attempt_budget
        with self.assertRaisesRegex(WalkthroughError, "budget is exhausted"):
            recover_walkthrough(enrollment, (1, 2, 3), (1, 2))

    def test_selection_parser_rejects_unsafe_or_ambiguous_input(self) -> None:
        allowed = (1, 2, 3, 4, 5)
        self.assertEqual(
            parse_identifiers(
                "",
                expected_count=3,
                allowed=allowed,
                default=(1, 2, 3),
            ),
            (1, 2, 3),
        )
        self.assertEqual(
            parse_identifiers("3, 1, 2", expected_count=3, allowed=allowed),
            (3, 1, 2),
        )
        for value in (
            "1,2",
            "1,1,2",
            "1,2,6",
            "1,2,three",
            "1;2;3",
            "1" * 65,
        ):
            with self.subTest(value=value):
                with self.assertRaises(WalkthroughError):
                    parse_identifiers(
                        value,
                        expected_count=3,
                        allowed=allowed,
                    )

    def test_interactive_wrong_then_correct_flow_prints_no_raw_records(self) -> None:
        answers = iter(("", "1,2,4", "", "y", "", "1,3"))
        output: list[str] = []

        status = run_interactive(
            input_function=lambda _: next(answers),
            output=output.append,
        )

        rendered = "\n".join(output)
        self.assertEqual(status, 0)
        self.assertIn('"outcome": "generic-rejection"', rendered)
        self.assertIn('"outcome": "success"', rendered)
        for contact in (
            "alpha@example.org",
            "beta@example.org",
            "gamma@example.org",
            "delta@example.org",
            "epsilon@example.org",
        ):
            self.assertNotIn(contact, rendered)
        self.assertEqual(exposed_categories(rendered, {}), [])


if __name__ == "__main__":
    unittest.main()
