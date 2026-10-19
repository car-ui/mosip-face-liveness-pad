"""Export the pinned upstream research model; PyTorch is only needed for this build step."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

COMMIT = "b6d5f04ad78778917853b25c778acef6d5626d15"
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, default=ROOT / "tmp" / "silent-face")
    parser.add_argument("--variant", choices=("v2", "v1se"), default="v2")
    args = parser.parse_args()
    # Only use the pinned source tree. Downloading it is an explicit model build step.
    source = args.upstream / "src/model_lib/MiniFASNet.py"
    v1se = args.variant == "v1se"
    weight_name = "4_0_0_80x80_MiniFASNetV1SE.pth" if v1se else "2.7_80x80_MiniFASNetV2.pth"
    weight_hash = ("84ee1d37d96894d5e82de5a57df044ef80a58be2b218b5ed7cdfd875ec2f5990" if v1se
                   else "a5eb02e1843f19b5386b953cc4c9f011c3f985d0ee2bb9819eea9a142099bec0")
    weights = args.upstream / "resources/anti_spoof_models" / weight_name
    if hashlib.sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != "e498c4ec5e1ddfaba62b941a126c19d65aa564999f3309661fe43ee8bf38acd7":
        raise ValueError("Unexpected upstream model source")
    if hashlib.sha256(weights.read_bytes()).hexdigest() != weight_hash:
        raise ValueError("Unexpected upstream model weights")
    spec = importlib.util.spec_from_file_location("upstream_minifasnet", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = (module.MiniFASNetV1SE if v1se else module.MiniFASNetV2)(conv6_kernel=(5, 5))
    state = torch.load(weights, map_location="cpu", weights_only=True)
    model.load_state_dict({k.removeprefix("module."): v for k, v in state.items()})
    model.eval()
    torch.set_num_threads(2)
    output = ROOT / ("assets/models/minifasnet_v1se.onnx" if v1se else "assets/models/minifasnet_v2.onnx")
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(model, torch.zeros(1, 3, 80, 80), str(output),
                      input_names=["input"], output_names=["logits"], opset_version=13,
                      dynamo=False)
    session = ort.InferenceSession(str(output), providers=["CPUExecutionProvider"])
    generator = np.random.default_rng(20261018)
    differences = []
    for _ in range(6):
        tensor = generator.uniform(0, 255, (1, 3, 80, 80)).astype(np.float32)
        with torch.no_grad():
            reference = model(torch.from_numpy(tensor)).numpy()
        actual = session.run(None, {"input": tensor})[0]
        np.testing.assert_allclose(actual, reference, rtol=2e-4, atol=2e-4)
        differences.append(float(np.max(np.abs(actual - reference))))
    manifest = {
        "profile": "minifasnet_v1se_4.0" if v1se else "minifasnet_v2_2.7", "version": "1.0.0",
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "upstreamRepository": "https://github.com/minivision-ai/Silent-Face-Anti-Spoofing",
        "upstreamCommit": COMMIT,
        "upstreamWeights": weights.name,
        "upstreamWeightsSha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "license": "Apache-2.0", "input": f"BGR float32 0..255, NCHW [1,3,80,80], {4.0 if v1se else 2.7}x crop",
        "output": "three logits; live class index 1; softmax once",
        "conversionValidation": {"randomTensors": 6, "maximumAbsoluteLogitDifference": max(differences)},
        "accuracyValidation": "NOT_EVALUATED. Conversion parity is not attack detection accuracy.",
    }
    output.with_suffix(".onnx.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (ROOT / "third_party").mkdir(exist_ok=True)
    (ROOT / "third_party/Silent-Face-Anti-Spoofing-LICENSE.txt").write_bytes((args.upstream / "LICENSE").read_bytes())
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
