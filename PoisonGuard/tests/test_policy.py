from poisonguard.data.schemas import Channel, Decision, Event, Sink
from poisonguard.methods.policy import DefaultPolicy


def test_sink_specific_policy_and_least_trust() -> None:
    policy = DefaultPolicy()
    typed = Event.create("preference", 1, "keyboard", Channel.TYPED, user_authored=True)
    remote = Event.create("message", 2, "sms", Channel.SMS, user_authored=False)
    assert policy.decide(typed, Sink.TRAIN) is Decision.ALLOW
    assert policy.decide(remote, Sink.MEMORY) is Decision.QUARANTINE
    assert policy.decide(remote, Sink.TRAIN) is Decision.DENY
    derived = Event.create("summary", 3, "service", Channel.DERIVED,
                           parent_ids=(typed.event_id, remote.event_id))
    assert policy.decide(derived, Sink.TRAIN, [Decision.ALLOW, Decision.DENY]) is Decision.DENY
