# Submission readiness status

Updated 26 October 2026 for MOSIP Decode 2026, Problem 04.

## Work included and verified

- Local face-liveness/PAD prototype, dataset evaluation tools, split-integrity
  checks, development-only threshold selector, native integration patches,
  pitch page, evaluation scorecard, demo checklist, and test protocols are in
  the source package.
- The Android, Desktop, and reference camera-SBI patches apply to their pinned
  upstream revisions. On 26 October, native preparation checks verified 21
  Desktop, 27 Android, and 32 camera-SBI source/assets with zero mismatches.
  Reports are in `integrations/native/evidence/native-preparation-20261026/`.
- The recorded full Python run passed 225 tests. The retained evidence
  integrity check passed 26 checksums. Earlier emulator runs passed 17
  Registration Client tests and eight camera-SBI tests with cameras disabled;
  those APKs predate the current source changes.
- The current working-tree source archive is
  `output/local/face-liveness-prototype.zip`. It is a verified source package,
  not a newly built Android or Desktop release.

## Nine non-L0/L1 criteria

All nine have prototype code or a test procedure in the repository. **All nine
remain partial at acceptance level** because their required field or live
integration evidence could not be collected in this workspace.

| Criterion | Completed prototype work | Acceptance evidence still missing |
|---|---|---|
| Mandatory 2: passive liveness | Strict evaluator, private split manifest, development threshold selection and reporting | Consented, independent development and held-out bona-fide/attack clips; frozen operating point and held-out results |
| Mandatory 3: presentation-attack detection | Fail-closed PAD path and per-attack-group evaluation support | Representative print, replay, mask and applicable injection trials or an authorized dataset |
| Mandatory 5: resident registration | Pinned client/SBI source patches and prior camera-disabled emulator evidence | Fresh current app builds and live camera-to-storage registration on a test identity |
| Mandatory 6: operator authentication | Role-specific capture gate and Desktop source build evidence | Current client/SBI build, live action flow and result with a test operator identity |
| Mandatory 7: supervisor authentication | Supervisor-specific policy and capture gate | Live supervisor flow, match/override behavior and audit evidence in a test environment |
| Mandatory 8: configuration | Policy serialization, strict SBI parsing, and policy-bound evidence checks | Fresh builds of both apps and end-to-end policy update/rejection demonstration |
| Mandatory 10: UI/UX | Responsive prototype, accessible interaction behavior, safe failure guidance, and ready-to-run study protocol | Consented participant sessions on target client screens and camera, followed by fixes and retest |
| Bonus: low-resource Android | One-CPU emulator benchmark and instrumentation | Current build measured on a representative physical ARM64 phone for latency, memory, energy and thermals |
| Bonus: hardware acceleration | Provider comparison and host profile; CPU/Azure output parity was exact, but all measured nodes ran on CPU | A supported Android GPU/NPU/NNAPI run with actual node placement and CPU parity |

L0/L1 vendor integration and multiple real-vendor support are separate criteria;
they are outside these nine. Neither is needed to run the nine checks above.

## Submission limits

No official contest submission has been sent. The workspace has no team/member
and institution details, jury-accessible hosted artifact link, or organizer
account access. A demo recording is also absent; the supplied guide marks video
as optional. The source package should not be described as a current Android
release, a live MOSIP deployment, an ISO certification, or a measured PAD
accuracy result.

The evaluation matrix and evidence boundaries are in
[`REQUIREMENTS_MATRIX.md`](REQUIREMENTS_MATRIX.md) and
[`LOCAL_DELIVERY_STATUS.md`](LOCAL_DELIVERY_STATUS.md).
