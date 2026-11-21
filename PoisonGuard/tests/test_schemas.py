from poisonguard.data.schemas import Channel, Event


def test_event_identity_is_deterministic_and_mutation_changes_it() -> None:
    args = dict(payload="hello", capture_time=1.0, app_id="keyboard",
                channel=Channel.TYPED, user_authored=True)
    first, second = Event.create(**args), Event.create(**args)
    assert first.event_id == second.event_id
    assert first.event_id != Event.create(**{**args, "payload": "changed"}).event_id
    assert Event.from_dict(first.to_dict()) == first


def test_event_validation() -> None:
    import pytest
    with pytest.raises(ValueError):
        Event.create("", 0, "app", Channel.SMS)
