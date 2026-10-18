# Android inference measurements

The native inference engine now selects one ONNX intra-op thread on a one-CPU system, with a maximum of two on larger systems. Inter-op threads are limited to one. The previous implementation always requested two intra-op threads.

The revised Android package passed all five instrumentation tests on a Google ATD API 34 x86_64 emulator with one virtual CPU and about 2 GB guest RAM. Tests include actual ONNX inference, ISO face decoding, and rejection before resident and operator-onboarding storage. The camera was disabled; the SBI parser and repositories are test doubles.

## Measured scope

Each measurement process performed ten warmups and 100 timed calls to `NativePadEngine.scoreTensor`. Input was a deterministic synthetic FP32 tensor with shape 1 by 3 by 80 by 80. The timed operation includes tensor creation, ONNX inference and softmax. It excludes image decoding, face detection, cropping, active challenges and a complete capture. Every measured score also had to match the Python reference.

The p50 and p95 values below are the 50th and 95th sorted observations out of 100. For example, p95 of 26.25 ms means 95 of those 100 calls took at most 26.25 ms. PSS is the whole Android target process's proportional memory use after the benchmark, including application code and libraries. It is not the model's additional memory cost.

| Build | Fresh process | Test mode | p50, ms | p95, ms | Process PSS, KiB |
|---|---|---|---:|---:|---:|
| Previous, two threads | 1 | Full five-test suite | 11.168 | 33.668 | 197772 |
| Previous, two threads | 2 | Benchmark only | 40.870 | 45.189 | 169732 |
| Previous, two threads | 3 | Benchmark only | 40.805 | 46.520 | 170149 |
| Adaptive, one thread | 1 | Full five-test suite | 8.871 | 25.706 | 189239 |
| Adaptive, one thread | 2 | Benchmark only | 21.450 | 26.252 | 168994 |
| Adaptive, one thread | 3 | Benchmark only | 21.065 | 23.794 | 168960 |

All six runs are retained in [the machine-readable report](../integrations/native/android-benchmark.json), which links each raw instrumentation log and its checksum. The emulator was rebooted between the two builds. Host scheduling and power state were not controlled. The lower times support avoiding excess inference threads on this one-CPU emulator. They do not establish a general speedup, physical-phone performance, battery use, or the latency of the full liveness workflow. The variation between the first and later processes also needs investigation before setting a performance target.

## Reproduction

Prepare and build the pinned Android client as described in `integrations/native/BUILD_NOTES.md`, including its instrumentation APK. Install the application and test APK on an isolated emulator. The full suite is:

```text
adb -s emulator-5554 shell am force-stop io.mosip.registration_client
adb -s emulator-5554 shell am instrument -w -r -e class io.mosip.registration_client.api_services.NativePadAcceptanceTest io.mosip.registration_client.test/androidx.test.runner.AndroidJUnitRunner
```

For an isolated benchmark process, use the same command with the class argument `io.mosip.registration_client.api_services.NativePadAcceptanceTest#actualAndroidInferenceTimingAndMemory`. Force-stop the application before each repeat. The final instrumentation result includes `facepadBenchmarkJson`. Keep the result and test status together, and record the application APK hash and device configuration.

The current ARM64 debug APK is 220,254,144 bytes and has not run on physical hardware. Its signature, ZIP integrity, ABI contents, packaged model hash and runtime notices were verified. A smaller APK and a successful emulator benchmark do not complete the low-resource Android requirement.

A later six-test landmark build ran in 36.023 seconds and measured PAD-tensor p50 17.902 ms, p95 46.955 ms and whole-process PSS 198222 KiB. An earlier landmark run took 80.685 seconds with p95 87.952 ms. Both raw outputs are retained in native evidence. These later results reinforce the host-load limitation; the earlier 24-26 ms p95 range is not a guaranteed operating point. The earlier landmark ARM64 APK is 223,712,618 bytes. Neither landmark inference nor a full camera workflow is included in those PAD-tensor timings.


The signed-active client build passes 12 tests in 63.239 seconds. Its synthetic PAD-tensor benchmark measured p50 29.406 ms, p95 89.091 ms and whole-process PSS 186092 KiB. This run occurred under host memory pressure and is not evidence of a performance improvement. Its ARM64 debug APK is 223,712,614 bytes and remains untested on hardware. The raw log and exact APK hashes are recorded under `signed_active_android` in `integrations/native/validation.json`.
