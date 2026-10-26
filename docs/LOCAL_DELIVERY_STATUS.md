# Local delivery status

Updated 26 October 2026. The implementation milestone is `de68e6f`; current
source and documentation are published on public GitHub `main` at
https://github.com/car-ui/mosip-face-liveness-pad. Commit `450f877` passed
Ubuntu, Windows, and camera-SBI CI. Later README-only changes also passed the
Ubuntu and Windows checks. External contest submission has not been performed.
The current repository still does not include a demo recording, team-specific
private submission details, physical devices/test participants, or an external
submission.

## Current implementation

The native frame session now applies the parsed action count, session timeout
and recovery limit. Previously those values were parsed but did not change the
fixed session. Desktop uses the configured timeout. Recovery clears all action
credit once per interrupted evidence episode and cannot extend the deadline.
Android checks signed action counts, ordered action types, session duration and
used retries against current policy before consuming the one-use transaction
ledger.

The working source now carries Android evidence version 2: the native session
attests its start time, timeout, action count, retry allowance and retries used
only after consuming the exact final JPEG. The Android checkpoint checks the
measured duration and retries against its current policy. These edits were made
after the retained October 20 build. Current camera-SBI source has since built
and passed camera-disabled instrumentation in CI run 40284447283. The current
Registration Client source still needs a fresh APK build; its retained APK
checksums describe the older milestone.

Android PAD rejection now shows a generic retry message to the user. Direct
checkpoint failures return a sanitized Flutter error, and face-capture SBI
failures use the same generic guidance. Detailed exception context stays in
internal logs for diagnostics.

The reference camera activity now accepts bounded action-count, blink/turn-pool,
timeout and retry extras and runs the requested session. A shared interop
capability validator and CLI cover the physical-webcam interface, mock device
and two simulated vendor adapters. Dataset reports now retain per-clip scores;
the new threshold selector accepts development reports only and enforces a
minimum class count plus a predeclared APCER ceiling. The full current Python
suite now passes. The local Android build toolchain remains unavailable; the
current reference SBI was built and tested on GitHub's runner.

The pinned desktop patch now connects active proof to operator authentication,
EOD supervisor authentication and face login. Face login passes a role-aware
capture gate into `SessionContext`, which rejects face authentication when a
caller omits the gate. The updated patch was prepared from a clean pinned
checkout and its five-module reactor compiled; live camera/UI acceptance is
still open.

The existing stable action-count display, preparation prompts, temporal PAD
evidence, portable YuNet detector, image bounds, exact-frame proof, role binding
and offline policy/model protections remain in place. See NATIVE_POLICY.md and
CONTINUATION_20261020.md for behavior and limitations.

## Executed checks

- Current full suite: 227 tests passed locally. Ubuntu and Windows CI passed
  the Python suite, evidence integrity checks, and actual Java/ONNX checks for
  commit `450f877`. The same source's camera-SBI build and camera-disabled
  instrumentation passed CI run 40284447283. These are software/emulator
  results, not physical or live identity acceptance.
- Fresh full Python suite on 23 October: 225 passed in 32.23 seconds wall time
  (32.155 seconds pytest time) with the exact locked dependencies under ignored
  `tmp/`; one Starlette/httpx deprecation warning was reported. The sanitized
  JUnit result is retained at
  `integrations/native/evidence/python-suite-20261023.xml`.
- Focused evaluation, manifest-integrity, interoperability and
  usability-protocol checks: 26 passed. The CLI report is retained in
  `integrations/native/evidence/interoperability-20261023.json`; its vendor
  adapters are simulated and it does not open the camera.
- Current Java 8 SBI policy checks: `NativePadPolicyCheck` and
  `CameraSbiRequestPolicyCheck` compiled and passed, including the cached
  workflow policy through object and list-of-maps `customOpts`, typed activity
  extras, defaults and fail-closed invalid settings.
- Earlier Python suite: 199 passed in 28.86 seconds on its then-current source.
- Clean code-package extraction: 205 file hashes verified; 199 tests passed
  in 16.68 seconds. Package commit de68e6f.
- Current pinned Desktop source build: five required reactor modules through
  `registration-client` passed Maven install with tests skipped. JDK 21 and a
  command-line Lombok 1.18.30 compatibility override were used; project source
  and POM files retain the pinned Lombok version. The native controller
  harness compiled but crashed in `onnxruntime.dll` during `OrtEnvironment`
  initialization on this host, so it does not establish current runtime
  acceptance.
- Latest Desktop patch: applied by the preparer to a clean checkout at the
  pinned upstream commit, then freshly compiled through all five reactor
  modules with Maven tests skipped. This used JDK 21, a Lombok 1.18.30
  command-line override and skipped the Git metadata plugin whose inherited
  `.git` path points inside child modules. No live camera/UI run was performed.
- Current ONNX provider benchmark: CPU and Azure outputs matched exactly, but
  the profile assigned all nodes to CPU. It observed no acceleration; Android
  GPU/NPU/NNAPI evidence remains open. See the retained [provider report and
  profile](../integrations/native/evidence/provider-benchmark-20261023/).
- Local simulator console loaded successfully at `http://127.0.0.1:4501/` and
  was visually checked with the simulator selected; no camera permission or
  real biometric capture was used.
- Java 11 desktop reactor: all five modules built, 1 minute 16 seconds.
- Retained Java 11 Desktop controller and JavaFX preview checks passed against
  the actual patched upstream components, with synthetic/recorded inputs.
- Native injected action checks passed for configured counts, recovery limits,
  timeout, PAD veto, sequence, clock and one-use exact-image proof.
- Registration Android split app and test APK build passed in 2 minutes;
  17 instrumentation tests passed in 32.998 seconds.
- Reference camera SBI app and test build passed in 1 minute 2 seconds;
  eight instrumentation tests passed in 61.596 seconds.
- All five APK signatures passed. App ZIP integrity, split ABIs, model hashes
  and license notices passed.
- All three prepared native checkouts matched their owned source/assets and
  integration patches. The final evidence validator passed 26 checksums.
- Fresh native preparation checks on 26 October passed for the exact pinned
  Desktop, Android, and camera-SBI revisions: 21, 27, and 32 source/assets,
  respectively, with zero mismatches and each patch present. Reports are under
  `integrations/native/evidence/native-preparation-20261026/`. These checks
  verify patch application and prepared files, not app builds or live capture.

Android execution used the named NATIVE_PAD_API34 emulator with cameras disabled.
The owned emulator was shut down after testing. No physical phone was operated.
Retained build reports bind APK hashes to prepared source fingerprints and logs.
Current reports and raw instrumentation are retained under
integrations/native/evidence/policy-session-20261020.

## Local artifacts

The current working-tree source archive is
[`output/local/face-liveness-prototype.zip`](../output/local/face-liveness-prototype.zip).
Its manifest verifies 234 included
source, test, documentation and evidence files, including the sanitized fresh
JUnit report, Android source-preparation record, working-tree edits and
non-ignored new files. The archive is source-only, not a newly built
Android/Desktop release.

The previous native APK artifacts were stored in `D:/CodexWork/`, which is not
available in this working folder. Their checksums and logs remain in
`integrations/native/validation.json` and
`integrations/native/evidence/policy-session-20261020/`. They validate the
earlier source milestone, not the current edits.

## Remaining requirements

Physical live/print/display/mask/injection evaluation, applying the selected
threshold to a separate held-out dataset, live official-client
camera-to-storage workflows, successful real identity matching, physical
Android and real L1/multiple-vendor integration remain unverified. Existing
observations are three Python webcam trials from one participant, not an
accuracy estimate or physical attack evaluation.

Native configuration is source-complete at prototype scope. Desktop supports
blink-only, turn-only and combined challenge pools. The pinned Android client
adds its cached resident/operator policy to the outbound face RCAPTURE request;
the reference SBI converts the standard `customOpts` object to its DAO's
list-based DTO, validates the values and passes them to its private camera
activity. Evidence version 2 lets Android compare completed actions, observed
duration and retries with its current policy. Java policy checks pass, and both
native patches plus the preparation workflow apply to their exact upstream
commits. The modified Registration Client still needs a fresh APK; the camera
SBI has current CI build/instrumentation evidence. The end-to-end policy-update
check remains open. Arbitrary action families, configurable
guidance, authenticated online synchronization and production device trust
remain open.

The hackathon mandatory scope is not declared complete. Tests and builds do not
replace the missing physical and live integration evidence. The original
supplied PDFs are tracked and included in the source package. No private
participant dataset is included. The required video, student credentials,
cloud deliverable uploads, and submission email remain missing; see
[`SUBMISSION_STATUS.md`](SUBMISSION_STATUS.md).
