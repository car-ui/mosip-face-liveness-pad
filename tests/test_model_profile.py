"""Model loading and conversion-contract checks, not attack accuracy tests."""
from pathlib import Path
import numpy as np
from src.core.passive_pad import ONNXModelPADBackend

MODEL = Path(__file__).resolve().parents[1] / 'assets/models/minifasnet_v2.onnx'


def test_packaged_model_loads_and_emits_finite_scores():
    assert MODEL.is_file(), 'The release must include its declared research PAD model'
    backend = ONNXModelPADBackend(str(MODEL))
    assert backend.is_available()
    assert backend.input_size == (80,80)
    assert backend.class_count == 3 and backend.live_index == 1
    assert backend.crop_scale == 2.7
    result = backend.evaluate(np.zeros((80,80,3), np.uint8))
    assert np.isfinite(result[:2]).all()
    assert 0 <= result[0] <= 1


def test_minifasnet_uses_bgr_raw_values_and_live_class_one(monkeypatch):
    backend = ONNXModelPADBackend(str(MODEL))
    seen=[]
    class Session:
        def run(self, names, inputs):
            seen.append(next(iter(inputs.values())))
            return [np.array([[0, 8, 0]],np.float32)]
    monkeypatch.setattr(backend,'_session',Session())
    image=np.zeros((80,80,3),np.uint8)
    image[:]=[10,100,200]
    score,*_=backend.evaluate(image)
    assert score > .99
    assert seen[0].shape == (1,3,80,80)
    np.testing.assert_array_equal(seen[0][0,:,0,0],[10,100,200])


def test_manifest_checksum_mismatch_prevents_loading(tmp_path):
    import json
    path=tmp_path/'model.onnx'
    path.write_bytes(MODEL.read_bytes())
    manifest=json.loads(Path(str(MODEL)+'.json').read_text())
    manifest['sha256']='0'*64
    Path(str(path)+'.json').write_text(json.dumps(manifest))
    assert not ONNXModelPADBackend(str(path)).is_available()


def test_reference_companion_model_has_distinct_crop_contract():
    model = MODEL.with_name("minifasnet_v1se.onnx")
    backend = ONNXModelPADBackend(str(model))
    assert backend.is_available()
    assert backend.crop_scale == 4.0
    assert backend.live_index == 1 and backend.class_count == 3
    assert np.isfinite(backend.evaluate(np.zeros((80, 80, 3), np.uint8))[:2]).all()


def test_mn3_uses_its_own_normalization_and_does_not_softmax_probabilities(monkeypatch):
    backend = ONNXModelPADBackend(str(MODEL.with_name("anti-spoof-mn3.onnx")))
    assert backend.is_available() and backend.crop_scale == 1.0
    assert backend.input_size == (128, 128) and backend.live_index == 0
    seen = []
    class Session:
        def run(self, names, inputs):
            seen.append(next(iter(inputs.values())))
            return [np.array([[.9, .1]], np.float32)]
    monkeypatch.setattr(backend, "_session", Session())
    image = np.full((128, 128, 3), [10, 100, 200], np.uint8)
    score, *_ = backend.evaluate(image)
    assert np.isclose(score, .9)
    expected = (np.array([200, 100, 10]) - [151.2405, 119.595, 107.8395]) / [63.0105, 56.457, 55.0035]
    np.testing.assert_allclose(seen[0][0, :, 0, 0], expected, atol=1e-6)


def test_mn3_rejects_invalid_probability_output(monkeypatch):
    import pytest
    backend = ONNXModelPADBackend(str(MODEL.with_name("anti-spoof-mn3.onnx")))
    class Session:
        def run(self, *args):
            return [np.array([[3, -2]], np.float32)]
    monkeypatch.setattr(backend, "_session", Session())
    with pytest.raises(ValueError, match="probabilities"):
        backend.evaluate(np.zeros((128, 128, 3), np.uint8))
