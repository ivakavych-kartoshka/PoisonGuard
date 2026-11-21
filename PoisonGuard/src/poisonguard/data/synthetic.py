"""Deterministic synthetic mobile-channel events for smoke tests only."""

from __future__ import annotations

import random
from poisonguard.data.schemas import Channel, Event


def generate_synthetic_events(seed: int = 7, benign_count: int = 8,
                              poison_count: int = 2) -> tuple[list[Event], set[str]]:
    if benign_count < 1 or poison_count < 0:
        raise ValueError("benign_count must be positive and poison_count nonnegative")
    rng = random.Random(seed)
    events: list[Event] = []
    for index in range(benign_count):
        events.append(Event.create(
            payload=f"benign preference {index}: tone {rng.choice(['brief', 'warm', 'formal'])}",
            capture_time=float(index + 1), app_id="keyboard.system", channel=Channel.TYPED,
            user_authored=True, metadata={"synthetic": True, "label": "benign"},
        ))
    poison_ids: set[str] = set()
    channels = [Channel.SMS, Channel.NOTIFICATION, Channel.CALENDAR, Channel.SHARE]
    for index in range(poison_count):
        event = Event.create(
            payload=f"SYNTHETIC_MARKER_{index} request target behavior",
            capture_time=float(benign_count + index + 1), app_id="untrusted.test",
            channel=channels[index % len(channels)], sender="synthetic-attacker",
            user_authored=False, metadata={"synthetic": True, "label": "poison"},
        )
        events.append(event)
        poison_ids.add(event.event_id)
    return events, poison_ids
