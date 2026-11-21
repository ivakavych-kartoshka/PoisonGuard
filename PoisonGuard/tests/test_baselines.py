import pytest
from poisonguard.baselines.external_wrappers import AMemGuardAdapter, ExternalDependencyUnavailable
from poisonguard.baselines.simple import NoDefensePolicy
from poisonguard.data.schemas import Channel, Decision, Event, Sink


def test_direct_and_external_baselines_are_distinct(tmp_path) -> None:  # type: ignore[no-untyped-def]
    event = Event.create("remote", 1, "app", Channel.SMS)
    assert NoDefensePolicy().decide(event, Sink.TRAIN) is Decision.ALLOW
    with pytest.raises(ExternalDependencyUnavailable):
        AMemGuardAdapter().run(tmp_path / "in", tmp_path / "out", {})
