from __future__ import annotations

import copy
import json
import unittest

from locus.flow_audit import (
    FLOW_PREFIX,
    TRACE_POLICY_ID,
    FlowAuditError,
    aggregate_events,
    parse_events,
)


def event(
    *,
    boot: str,
    sequence: int,
    observation: str,
    receiver: str = "admission",
    context: str = "NF01:yi-2of3",
    category: str = "admission-issue",
) -> dict[str, object]:
    return {
        "boot": boot,
        "category": category,
        "context": context,
        "observation": observation,
        "receiver": receiver,
        "request_bytes": 17,
        "response_bytes": 23,
        "result": "success",
        "sender": "managed-client",
        "sequence": sequence,
        "trace_policy_id": TRACE_POLICY_ID,
    }


class FlowAuditTests(unittest.TestCase):
    def test_prefixed_events_deduplicate_and_reconcile(self) -> None:
        first = event(boot="11" * 8, sequence=1, observation="sender")
        second = event(boot="22" * 8, sequence=1, observation="receiver")
        logs = [FLOW_PREFIX + json.dumps(first), FLOW_PREFIX + json.dumps(second)]
        contacts = aggregate_events(parse_events(logs + logs))
        self.assertEqual(contacts["NF01:yi-2of3"][0]["reconciliation"], "matched")
        self.assertEqual(contacts["NF01:yi-2of3"][0]["request_count"], 1)

    def test_multiplexed_prefixed_events_on_one_line_are_bounded(self) -> None:
        first = event(boot="11" * 8, sequence=1, observation="sender")
        second = event(boot="22" * 8, sequence=1, observation="receiver")
        combined = (
            "service-a | "
            + FLOW_PREFIX
            + json.dumps(first)
            + FLOW_PREFIX
            + json.dumps(second)
        )
        self.assertEqual(len(parse_events([combined])), 2)
        with self.assertRaises(FlowAuditError):
            parse_events([combined + " unexpected"])

    def test_unknown_gap_mismatch_and_noresolver_contact_fail_closed(self) -> None:
        base = event(boot="11" * 8, sequence=1, observation="sender")
        changed = copy.deepcopy(base)
        changed["category"] = "unknown"
        with self.assertRaises(FlowAuditError):
            parse_events([FLOW_PREFIX + json.dumps(changed)])
        gap = copy.deepcopy(base)
        gap["sequence"] = 2
        with self.assertRaises(FlowAuditError):
            parse_events([FLOW_PREFIX + json.dumps(gap)])
        receiver = event(boot="22" * 8, sequence=1, observation="receiver")
        receiver["response_bytes"] = 24
        with self.assertRaises(FlowAuditError):
            aggregate_events([base, receiver])
        resolver = event(
            boot="33" * 8,
            sequence=1,
            observation="sender",
            receiver="resolver",
            category="resolver-resolve",
        )
        with self.assertRaises(FlowAuditError):
            aggregate_events([resolver])

    def test_fixed_available_provider_uses_one_observation_side(self) -> None:
        provider = event(
            boot="11" * 8,
            sequence=1,
            observation="sender",
            receiver="provider",
            category="object-read",
        )
        provider["sender"] = "storage-gateway"
        contacts = aggregate_events([provider])
        self.assertEqual(
            contacts["NF01:yi-2of3"][0]["reconciliation"], "fixed-available"
        )

    def test_unavailable_sender_only_fault_is_narrowly_reconciled(self) -> None:
        sender = event(boot="11" * 8, sequence=1, observation="sender")
        sender["result"] = "unavailable"
        sender["response_bytes"] = 0
        contacts = aggregate_events([sender])
        self.assertEqual(contacts["NF01:yi-2of3"][0]["unavailable_count"], 1)
        sender["result"] = "success"
        with self.assertRaises(FlowAuditError):
            aggregate_events([sender])


if __name__ == "__main__":
    unittest.main()
