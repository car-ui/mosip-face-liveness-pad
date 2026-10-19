"""Offline policy validation and atomic persistence, without credentials/model paths."""
import json
import pytest
from src.core.config import LivenessConfig, WorkflowType
from src.core.policy_store import PolicyStore, PolicyUpdate, apply_update


def test_policy_roundtrip_keeps_runtime_model_path_out_of_document(tmp_path):
    store = PolicyStore(tmp_path / "policy.json")
    original = LivenessConfig(onnx_model_path="private/runtime/model.onnx")
    changed = apply_update(original, PolicyUpdate(workflow=WorkflowType.OPERATOR_AUTHENTICATION,
                                                 passive_threshold=.93, min_challenges=3))
    store.save(changed)
    assert "private/runtime" not in store.path.read_text()
    restored = store.load(LivenessConfig(onnx_model_path="different/runtime/model.onnx"))
    assert restored.operator_policy.passive_threshold == .93
    assert restored.operator_policy.min_challenges == 3
    assert restored.operator_policy.max_challenges >= 3
    assert restored.onnx_model_path == "different/runtime/model.onnx"


def test_failed_atomic_replace_preserves_previous_policy(tmp_path, monkeypatch):
    store = PolicyStore(tmp_path / "policy.json")
    store.save(LivenessConfig())
    old = store.path.read_bytes()
    def fail(*args):
        raise OSError("simulated disk failure")
    monkeypatch.setattr("src.core.policy_store.os.replace", fail)
    with pytest.raises(OSError):
        store.save(LivenessConfig())
    assert store.path.read_bytes() == old
    assert list(tmp_path.glob("*.tmp")) == []


def test_conflicting_global_values_are_rejected(tmp_path):
    store = PolicyStore(tmp_path / "policy.json")
    store.save(LivenessConfig())
    content = json.loads(store.path.read_text())
    content["updates"][0]["liveness_enabled"] = False
    store.path.write_text(json.dumps(content))
    with pytest.raises(ValueError, match="Conflicting"):
        store.load(LivenessConfig())


def test_required_operator_actions_cannot_be_disabled_from_file(tmp_path):
    store = PolicyStore(tmp_path / "policy.json")
    store.save(LivenessConfig())
    content = json.loads(store.path.read_text())
    for row in content["updates"]:
        if row["workflow"] == "OPERATOR_AUTHENTICATION":
            row["active_liveness_enabled"] = False
    store.path.write_text(json.dumps(content))
    with pytest.raises(ValueError, match="Required active"):
        store.load(LivenessConfig())


@pytest.mark.parametrize("change", [
    lambda p: p.update(schemaVersion=99),
    lambda p: p.update(secret="must not load"),
    lambda p: p["updates"][0].update(passive_threshold=.1),
    lambda p: p["updates"][0].update(workflow="OPERATOR_AUTHENTICATION"),
])
def test_invalid_policy_documents_fail_closed(tmp_path, change):
    store = PolicyStore(tmp_path / "policy.json")
    store.save(LivenessConfig())
    content = json.loads(store.path.read_text())
    change(content)
    store.path.write_text(json.dumps(content))
    with pytest.raises(ValueError):
        store.load(LivenessConfig())
