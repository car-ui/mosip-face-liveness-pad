# Local delivery status

Updated 20 October 2026. Work resumed from the freshly fetched GitHub commit
`a4d851c`. The code milestone is `de68e6f`; later delivery commits retain its
build evidence and this checkpoint. Publication and merge to main are authorized.
Demo recording, visibility changes and external submission remain excluded.

## Current implementation

The native frame session now applies the parsed action count, session timeout
and recovery limit. Previously those values were parsed but did not change the
fixed session. Desktop uses the configured timeout. Recovery clears all action
credit once per interrupted evidence episode and cannot extend the deadline.
Android checks that signed action counts are bounded and meet the current
policy minimum before consuming the one-use transaction ledger.

The existing stable action-count display, preparation prompts, temporal PAD
evidence, portable YuNet detector, image bounds, exact-frame proof, role binding
and offline policy/model protections remain in place. See NATIVE_POLICY.md and
CONTINUATION_20261020.md for behavior and limitations.

## Executed checks

- Full Python suite: 199 passed in 28.86 seconds on the working source.
- Clean code-package extraction: 205 file hashes verified; 199 tests passed
  in 16.68 seconds. Package commit de68e6f.
- Java 11 desktop reactor: all five modules built, 1 minute 16 seconds.
- Desktop controller and JavaFX preview checks: both passed against the actual
  patched upstream components, with synthetic/recorded inputs.
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

Android execution used the named NATIVE_PAD_API34 emulator with cameras disabled.
The owned emulator was shut down after testing. No physical phone was operated.
Retained build reports bind APK hashes to prepared source fingerprints and logs.
Current reports and raw instrumentation are retained under
integrations/native/evidence/policy-session-20261020.

## Local artifacts

Artifact root: D:/CodexWork/native-face-pad-20261018.

- APKs and combined report: artifacts/native-final-20261020/summary.json.
- Verified code archive: artifacts/face-liveness-source-de68e6f.zip.
- That archive SHA-256:
  c2c53131b0d3684fafc38eb4764108d03e945017128e6e7e606ebbd85c6db2d6.
- The laptop launcher is artifacts/START-LAPTOP-PHYSICAL-TRIAL.cmd. It was
  retargeted to the tested code extraction and passed --check without a camera.
- Checkpoint and later packaging details are in RESUME_CHECKPOINT.md.

## Remaining requirements

Physical live/print/display/mask/injection evaluation, frozen-threshold
calibration, live official-client camera-to-storage workflows, successful real
identity matching, physical Android and real L1/multiple-vendor integration
remain unverified. Existing observations are three Python webcam trials from
one participant, not an accuracy estimate or physical attack evaluation.

Native configuration also remains partial. The reference camera emits two-action
version 1 evidence. It satisfies client minima of one or two and cannot fulfill
three or four. Its signed contract lacks session start, retry count and a full
policy snapshot, so client timeout/retry enforcement across the Android/SBI
boundary is not established. Native custom action pools, configurable guidance,
authenticated online synchronization and production device trust remain open.

The hackathon mandatory scope is not declared complete. Tests and builds do not
replace the missing physical and live integration evidence. Original supplied
PDFs and private camera material are excluded from Git.