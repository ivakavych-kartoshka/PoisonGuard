import numpy as np
from poisonguard.data.schemas import Channel, Decision, EnvironmentRecord, Event, Sink
from poisonguard.methods.core import PoisonGuardEngine
from poisonguard.baselines.simple import NoDefensePolicy
from poisonguard.data.schemas import NodeType


def environment() -> EnvironmentRecord:
    return EnvironmentRecord("code", "model", "tok", "opt", "policy", "cpu", 1)


def test_algorithm_one_admits_typed_denies_remote_training_and_promotes() -> None:
    engine = PoisonGuardEngine(environment())
    typed = Event.create("my preference", 1, "keyboard", Channel.TYPED, user_authored=True)
    remote = Event.create("external", 2, "sms", Channel.SMS, user_authored=False)
    assert engine.ingest(typed)[Sink.TRAIN] is Decision.ALLOW
    assert engine.ingest(remote)[Sink.TRAIN] is Decision.DENY
    candidate = engine.train_candidate()
    report = engine.audit_and_promote(candidate, np.eye(engine.trainer.dimension))
    assert report.passed
    assert engine.active_checkpoint_id in engine.checkpoints
    assert remote.event_id not in engine.checkpoints[engine.active_checkpoint_id].source_ids


def test_cross_sink_laundering_path_is_explicit_and_revocable() -> None:
    engine = PoisonGuardEngine(environment(), NoDefensePolicy())
    remote = Event.create("external memory content", 1, "sms", Channel.SMS, user_authored=False)
    engine.ingest(remote)
    memory_id = next(iter(engine.memory))
    example_id = engine.create_training_example_from_memory(memory_id)
    candidate = engine.train_candidate([example_id])
    assert engine.audit_and_promote(candidate, np.eye(engine.trainer.dimension)).passed
    active = engine.active_checkpoint_id
    descendants = engine.graph.descendants({remote.event_id})
    assert {memory_id, example_id, candidate, active}.issubset(descendants)
    engine.revoke_and_recover([remote.event_id])
    assert all(not engine.graph.nodes[item].valid for item in descendants
               if engine.graph.nodes[item].node_type is not NodeType.EVENT or item == remote.event_id)
