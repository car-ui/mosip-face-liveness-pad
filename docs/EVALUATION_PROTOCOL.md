# PAD and workflow evaluation protocol

The automated suite proves defined software properties. A separate collection and evaluation process is needed to measure whether people and attacks are classified correctly. Keep those evidence types separate in the pitch.

## Collect and split data

Use consented participants and documented presentation attack instruments. Include printed photos with different papers/finishes, phone/tablet/monitor replays, changing illumination, camera models, distance, motion, glasses, face pose, and applicable mask attacks. Record each device, capture software, attack medium, lighting condition, and model/configuration version privately.

Split participants and attack sources into development and test groups before selecting thresholds. Choose a threshold using development data. Freeze the model, crop/preprocessing, and threshold before evaluating held-out test clips. Do not tune on test failures and retain the original test score as if it were independent.

## Passive evaluation and threshold selection

Create one private master JSONL manifest next to the videos. Include both
splits before evaluating either split, so the loader can check the participant
and attack-source separation:

```json
{"path":"bona-fide/dev-01.mp4","label":"bona_fide","subject_group":"subject-dev-01","split":"development"}
{"path":"attacks/dev-print-01.mp4","label":"attack","pai":"matte-print","attack_source_group":"print-source-dev-01","subject_group":"subject-dev-01","split":"development"}
{"path":"bona-fide/test-01.mp4","label":"bona_fide","subject_group":"subject-test-01","split":"test"}
{"path":"attacks/test-print-01.mp4","label":"attack","pai":"matte-print","attack_source_group":"print-source-test-01","subject_group":"subject-test-01","split":"test"}
```

`subject_group` and `attack_source_group` are private pseudonyms. Use the same
subject pseudonym for that person's bona-fide and attack clips, and a distinct
attack-source pseudonym for each physical presentation source. The evaluator
requires both classes in both splits, checks that neither group crosses the
development/test boundary, rejects duplicate or out-of-folder video paths, and
omits the pseudonyms and paths from its output. Keep this manifest private.

Run `scripts/evaluate_dataset.py` on the development split first. It analyzes up to the configured frame count per clip, detects a single acceptable-quality face, runs strict ONNX PAD, and records the mean valid-frame live score for each clip. Then select a candidate threshold against a predeclared development APCER ceiling:

```powershell
python scripts/evaluate_dataset.py pad-master.jsonl --split development --model assets/models/minifasnet_v2.onnx --output output/local/pad-development.json
python scripts/select_pad_threshold.py output/local/pad-development.json --max-apcer 0.05 --minimum-per-class 20 --output output/local/pad-threshold.json
```

The selector only accepts a development report. It considers only thresholds in the runtime-supported range 0.46-0.99, requires the configured minimum number of classified attack and bona fide clips, ignores nonresponses in APCER/BPCER while reporting their counts, and breaks BPCER ties by choosing the lower threshold. The target APCER and minimum class count must be chosen before examining results; neither is an ISO certification claim.

Freeze the selected threshold, model and preprocessing before evaluating the held-out test split. Use a separate manifest and the exact selected threshold:

```powershell
python scripts/evaluate_dataset.py pad-master.jsonl --split test --model assets/models/minifasnet_v2.onnx --threshold 0.82 --output output/local/pad-test.json
```

Replace `0.82` with the value written to `pad-threshold.json`. Keep the development and test participants and attack sources separate. Do not feed a test report back into threshold selection. The per-clip mean-score aggregation is a declared research protocol, not a claim that it implements every ISO/IEC 30107-3 procedure.

Reported APCER is the fraction of classified attack clips accepted. Reported BPCER is the fraction of classified bona fide clips rejected. Clips with no usable frames or no valid PAD results are nonresponses and are excluded from those two denominators, then reported separately. Always present counts and nonresponses alongside rates. Report APCER separately for each instrument group; a pooled average can conceal a weak group. Zero observed errors on a small set is not a population guarantee.

The output contains aggregate counts, attack-group rates, clip-level labels/outcomes, the model checksum, threshold, and p50/p95 processing latency. It omits video paths and participant identifiers. Keep the input videos and manifest outside the public submission. This tool evaluates passive PAD, not random active challenges or the complete registration/authentication workflow.

## Active and complete workflow evaluation

For each workflow and each native platform, test pass, wrong action, no action, timeout, face loss, face substitution, repeated sequence, PAD attack introduced during an action, device disconnect, retry exhaustion, and offline operation. Record whether final capture acceptance or authentication actually occurred. An API error message alone does not prove that the client blocked its final action.

Recorded clips cannot respond to a new random challenge. They are useful attack fixtures, but are not a substitute for real bona fide subjects following prompts. Test adaptive screen replays and generated facial actions where appropriate. Keep action false accepts/rejects separate from passive PAD results.

## Interoperability and performance

Build a matrix of official client version, OS, device/vendor, supported pixel format, frame rate/resolution, model hash, provider, and online/offline state. Measure p50/p95 end-to-end capture and per-frame processing latency, completed challenge duration, retry/failure rates, peak memory, power, and thermal behavior on low-resource Android hardware. Repeat accelerated and CPU runs with numerical parity checks.

On a host where ONNX Runtime has CPU and accelerator providers installed, run
`scripts/benchmark_onnx_providers.py --output output/local/provider-benchmark.json`.
It uses the same deterministic FP32 tensor for every provider, records p50/p95
latency, checks absolute output error against CPU, and reads the ONNX Runtime
profile for provider node assignments. A provider appearing in the available or
active list does not count as acceleration; inspect `accelerationObserved` and
the per-provider assignment counts. This host harness does not establish Android
NNAPI/GPU/NPU behavior, full-frame timing, power draw, or PAD accuracy. Use the
official app's physical-device benchmark for those results.

No physical dataset or official native-client E2E result has been generated by the automated unit tests in this repository. The inherited image transformations in `test_photo_spoof_simulation.py` are developer-fixture experiments, including recorded photos. Do not present them as measured bona fide human detection accuracy.
