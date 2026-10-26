# Submission readiness status

Updated 26 October 2026 for MOSIP Decode 2026, Problem 04.

## Audit against the original submission guide

All three pages of `Submission_Guidelines_MOSIP_Decode_2026.pdf` were rechecked,
including the visible mandatory asterisks. **Video Demo is starred as mandatory.**
Its description says a team "can submit" a video, but that wording does not
remove the mandatory marking. Earlier repository notes calling the video
optional were incorrect; treat the recording as required unless MOSIP waives it.

| Starred deliverable | Current state | Remaining submission action |
|---|---|---|
| Source code | Included and published on public GitHub `main` | Supply the repository URL in the submission email |
| Working prototype or demo | Local browser and desktop prototype included with setup instructions | Share a jury-accessible runnable/demo artifact; full native and physical acceptance remains partial |
| Pitch presentation or slide deck | Nine-slide HTML deck in `pitch/index.html` | Final team details, explicit stack/audience/impact review, rehearsal, and cloud deliverable link |
| Video demo | Missing | Record and review a typical 2-5 minute demonstration; label simulator scenes and disclose field-validation limits |
| Usage and installation instructions | Included in `README.md` and native guides | Verify the exact jury setup and shared artifact links |
| API documentation, if applicable | Included in `docs/API.md` and local OpenAPI | Share documentation with the source/demo links |
| Git repository with version history | Public repository and commit history available | Supply its URL and check access without signing in |
| College/university credentials | Missing | Each student must upload a valid institution ID through the authorized private submission process |

The source repository is https://github.com/car-ui/mosip-face-liveness-pad.
Anonymous GitHub API access confirmed it is public and `main` is the default
branch. Supporting architecture/sequence diagrams, fixture data, test cases,
and results are included. A separate wireframe/mockup export and representative
physical PAD dataset are not included. The original supplied PDFs are included
in the source ZIP.

The guide also requires cloud-storage links for the other mandatory artifacts
and an email to `decode@mosip.io` containing the team name, problem statement,
and URLs. Those uploads, private student credentials, team details, submission
email, and organizer acknowledgement remain outstanding.

## Work included and verified

- Local face-liveness/PAD prototype, dataset evaluation tools, split-integrity
  checks, development-only threshold selector, native integration patches,
  pitch page, evaluation scorecard, demo checklist, and test protocols are in
  the source package.
- The Android, Desktop, and reference camera-SBI patches apply to their pinned
  upstream revisions. On 26 October, native preparation checks verified 21
  Desktop, 27 Android, and 32 camera-SBI source/assets with zero mismatches.
  Reports are in `integrations/native/evidence/native-preparation-20261026/`.
- The current full Python run passed 227 tests, and Ubuntu/Windows CI passed
  through the native Java/ONNX checks. Raw log bytes now survive Git checkouts
  without invalidating the 26 retained evidence checksums. The current camera
  SBI built and passed camera-disabled emulator instrumentation in
  [CI run 40284447283](https://github.com/car-ui/mosip-face-liveness-pad/actions/runs/40284447283).
  The retained 17-test Android Registration Client APK evidence is older;
  that client's current source still needs a fresh APK build.
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
| Mandatory 5: resident registration | Pinned client/SBI source patches, current camera-SBI CI build and earlier client emulator evidence | Fresh current Registration Client APK and live camera-to-storage registration on a test identity |
| Mandatory 6: operator authentication | Role-specific capture gate and Desktop source build evidence | Current client/SBI build, live action flow and result with a test operator identity |
| Mandatory 7: supervisor authentication | Supervisor-specific policy and capture gate | Live supervisor flow, match/override behavior and audit evidence in a test environment |
| Mandatory 8: configuration | Policy serialization, strict SBI parsing, policy-bound evidence checks, and current camera-SBI CI build | Fresh current Registration Client APK and end-to-end policy update/rejection demonstration |
| Mandatory 10: UI/UX | Responsive prototype, accessible interaction behavior, safe failure guidance, and ready-to-run study protocol | Consented participant sessions on target client screens and camera, followed by fixes and retest |
| Bonus: low-resource Android | One-CPU emulator benchmark and instrumentation | Current build measured on a representative physical ARM64 phone for latency, memory, energy and thermals |
| Bonus: hardware acceleration | Provider comparison and host profile; CPU/Azure output parity was exact, but all measured nodes ran on CPU | A supported Android GPU/NPU/NNAPI run with actual node placement and CPU parity |

L0/L1 vendor integration and multiple real-vendor support are separate criteria;
they are outside these nine. Neither is needed to run the nine checks above.

## Submission limits

No official contest submission has been sent. Source code is public, but the
other mandatory deliverables have not been uploaded to cloud storage. Team and
institution details, student credential uploads, and the required video are
absent. The source package should not be described as a current Registration
Client Android release, a live MOSIP deployment, an ISO certification, or a
measured PAD accuracy result.

The evaluation matrix and evidence boundaries are in
[`REQUIREMENTS_MATRIX.md`](REQUIREMENTS_MATRIX.md) and
[`LOCAL_DELIVERY_STATUS.md`](LOCAL_DELIVERY_STATUS.md).
