"""Ordering and construction helpers for the D030 affordable collector."""

from __future__ import annotations

import hashlib
from typing import cast

from .affordable_performance_evidence import scheduled_slots

ORDER_DOMAIN = "LOCUS/managed-performance-order/v2"


def ordered_arm_block_slots(arm_id: str, block: int) -> tuple[dict[str, object], ...]:
    selected = [
        slot
        for slot in scheduled_slots()
        if slot["arm_id"] == arm_id and slot["block"] == block
    ]
    warmups = [slot for slot in selected if slot["scenario_id"] == "AP00"]
    if len(warmups) != 1 or len(selected) != 27:
        raise ValueError("affordable arm/block membership changed")
    measured = [slot for slot in selected if slot["scenario_id"] != "AP00"]
    seed = cast(int, warmups[0]["seed"])

    def key(slot: dict[str, object]) -> str:
        material = f"{ORDER_DOMAIN}:{seed}:{arm_id}:{slot['slot_id']}".encode("ascii")
        return hashlib.sha256(material).hexdigest()

    return (warmups[0], *sorted(measured, key=key))


__all__ = ["ORDER_DOMAIN", "ordered_arm_block_slots"]
