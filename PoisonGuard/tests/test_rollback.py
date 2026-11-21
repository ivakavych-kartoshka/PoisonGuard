import numpy as np
from poisonguard.baselines.simple import NoDefensePolicy
from poisonguard.data.schemas import Channel, EnvironmentRecord, Event
from poisonguard.methods.core import PoisonGuardEngine


def env() -> EnvironmentRecord:
    return EnvironmentRecord("code", "model", "tok", "opt", "policy", "cpu", 4)


def train(events):  # type: ignore[no-untyped-def]
    engine = PoisonGuardEngine(env(), NoDefensePolicy())
    for event in events:
        engine.ingest(event)
    candidate = engine.train_candidate()
    assert engine.audit_and_promote(candidate, np.eye(8)).passed
    return engine


def test_exact_rollback_matches_clean_counterfactual() -> None:
    benign = [Event.create(f"benign {i}", i + 1, "keyboard", Channel.TYPED, user_authored=True)
              for i in range(3)]
    poison = Event.create("synthetic poison", 4, "app", Channel.SMS, user_authored=False)
    clean = train(benign)
    attacked = train([*benign, poison])
    certificate = attacked.revoke_and_recover([poison.event_id], "probe")
    assert certificate.exact and certificate.status == "complete"
    assert np.array_equal(attacked.parameters, clean.parameters)
    assert poison.event_id not in attacked.checkpoints[attacked.active_checkpoint_id].source_ids
