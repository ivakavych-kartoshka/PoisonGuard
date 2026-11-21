import json
from poisonguard.data.adapters import JsonlEventAdapter
from poisonguard.data.synthetic import generate_synthetic_events


def test_synthetic_data_is_reproducible() -> None:
    a, pa = generate_synthetic_events(3, 4, 2)
    b, pb = generate_synthetic_events(3, 4, 2)
    assert [x.event_id for x in a] == [x.event_id for x in b]
    assert pa == pb and len(pa) == 2


def test_jsonl_adapter(tmp_path) -> None:  # type: ignore[no-untyped-def]
    event = generate_synthetic_events(1, 1, 0)[0][0]
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps(event.to_dict()) + "\n", encoding="utf-8")
    assert list(JsonlEventAdapter(path).iter_events()) == [event]
