# Evaluation rubric evidence map

This map follows the supplied MOSIP Decode 2026 evaluation criteria. It links each weighted category to evidence in this repository and records limits that materially affect an evaluator's assessment. It is not a predicted jury score.

The requirement matrix classifies 16 of 27 items as implemented at their stated
prototype scope and 11 as partial. The Android/SBI evidence-v2 and configurable
camera action-pool changes are in the working source, including cached-policy
serialization into SBI `customOpts` and strict camera-side parsing. The retained
APKs and emulator reports predate these changes; they need a fresh platform
build before they can be presented as packaged Android evidence. A
development-only threshold selector and a portable device capability-contract
check are also included.

## Functionality completion - 40%

**Evidence available:** the local prototype implements passive PAD, temporal checks, automatically selected active actions, role-specific policy, retry/timeout handling, explicit simulators, and fail-closed capture decisions. Pinned Desktop and Android source patches add native capture checkpoints; the reference camera SBI binds its signed active result to its transaction and exact ISO image. The recorded code milestone passed 199 Python tests, a five-module Desktop build and controller checks, 17 Android Registration Client emulator tests, and eight reference-SBI emulator tests. See the [requirement matrix](REQUIREMENTS_MATRIX.md), [local delivery status](LOCAL_DELIVERY_STATUS.md), and [`integrations/native/validation.json`](../integrations/native/validation.json).

**Material limit:** mandatory real-world acceptance is incomplete. No representative physical attack evaluation, live successful native camera-to-storage flow, production certificate-chain trust, or real L0/L1 vendor integration is established. The emulator cameras were disabled; fixture signatures and action metadata are not production trust or human action evidence.

## Quality of deliverable - 40%

**Evidence available:** the repository includes pinned dependencies, installation/API guides, a technical design, sequence diagrams, model card, licenses/notices, a requirement-by-requirement evidence matrix, an evaluation protocol, and reproducible native preparation/check scripts. Python, Java, Android source and packaged-model checks have retained results. Secure update handling, bounded image decoding, exact-image proof, transaction replay checks and error paths have dedicated regression coverage.

**Material limit:** some deployment work remains, including production key provisioning and revocation, physical-device profiling, cross-vendor format coverage, and review of inherited bundled JAR terms before redistributing the reference SBI APK. Test evidence is tied to the recorded code milestone and configurations; it is not an independent quality certification.

## User experience and design - 10%

**Evidence available:** the local console presents camera/simulator status, face-positioning guidance, passive progress, automatic action prompts, failure reasons, retry state and diagnostics. It supports keyboard focus and live announcements. The repository also contains a responsive browser pitch and workflow diagrams.

**Material limit:** a task-based [human-study protocol](USABILITY_STUDY.md) is ready, but no structured accessibility/usability results are recorded. Full Desktop and Android user-interface workflows have not been demonstrated with a live person and physical camera. Localization and accessibility alternatives need human review.

## Presentation and communication - 10%

**Evidence available:** [`pitch/index.html`](../pitch/index.html) contains a nine-slide, self-contained presentation with problem framing, solution, architecture, policies, model contract, test evidence and explicit limitations. [`DEMO_AND_SUBMISSION.md`](DEMO_AND_SUBMISSION.md) provides a timed jury-demo script and submission checklist.

**Material limit:** the supplied submission guide treats a 2-5 minute demo video as optional; no recording is included. A concise recording could still strengthen the presentation. The pitch also needs the real team name, member/institution details, rehearsal, and final accessible artifact links. Those details are not in this repository.

## High-complexity problem statement

The supplied Problem 04 statement is marked **High** complexity. The repository demonstrates work across PAD inference, challenge response, native client checkpoints, offline policy, model updates, security controls and test automation. The remaining physical and production integration evidence is central to judging how much of that high-complexity scope is complete.

## Final submission items outside the repository

- Optionally record and inspect a 2-5 minute video, using a consented live subject for any human-action footage and labeling simulated scenes.
- Add the team's actual name, members and institution details to the private submission materials.
- Obtain and submit student credentials through the organizer's private process; do not commit them to source control.
- Place source and supporting artifacts at accessible URLs and verify those URLs while signed out.
- Send the team name, problem statement and URLs to `decode@mosip.io` through the team's authorized submission process.
- Complete physical L0/L1, attack, usability and live official-client validation before making claims that depend on those results.
