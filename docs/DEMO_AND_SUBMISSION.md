# Demo and submission checklist

The prototype can demonstrate local processing, policy enforcement, attack-fixture rejection, clear failure handling, and secure model update checks. Native MOSIP integration and physical attack evaluation remain the main mandatory gaps. Close them before describing the project as complete.

## A 3-minute jury demo

1. **0:00-0:25. State the problem.** A face image must not be accepted merely because a camera returned it. Explain that PAD checks the presentation and that actions provide an additional check. State which native integrations are actually demonstrated.
2. **0:25-0:55. Show the running console.** Select a simulator, point out its label, then switch to a consented physical camera demonstration if one has been prepared. Show live positioning and passive evaluation.
3. **0:55-1:30. Show active verification.** Use a real subject and follow the automatically selected action. Operator/supervisor profiles require actions. Do not manually mark a challenge complete or lower the threshold to manufacture success.
4. **1:30-1:55. Demonstrate rejection.** Show the screen-replay fixture, a missing/multiple-face scenario, or a physical attack already covered by your protocol. Show that no biometric payload is returned. Label fixture evidence as simulation.
5. **1:55-2:25. Explain the engineering.** PAD runs during active verification; preview cannot advance decisions; one capture owns the device; errors fail closed. Show anonymous counters and model provenance in diagnostics.
6. **2:25-3:00. Present evidence and limits.** Show test results, model conversion parity, signed update checks, and the remaining device/native evaluation plan. Give actual measured results only. Finish with the operational value of local processing and the next acceptance test.

Practice with the exact packaged code and chosen device. Pre-download dependencies, disconnect the network, rehearse pass/failure paths, and time the full recording. Avoid filming private IDs, tokens, credentials, or unconsented faces.

## Mandatory and supporting submission artifacts

- Complete, runnable source repository with accessible history and dependency instructions.
- Stable working prototype/demo.
- Pitch deck with problem, solution, stack, intended users, impact, and evidence limits.
- Required video demo, typically 2-5 minutes. The original guide marks "Video Demo*" as mandatory; no recording is currently included. Earlier notes describing it as optional were incorrect.
- Usage and installation instructions.
- API documentation where applicable.
- Student college/university credentials through the organizer's private process. Never commit them here.

The submission guide also lists mockups, architecture diagrams, sample test data, and test results as supporting artifacts. This repository contains architecture/sequence diagrams, sample fixtures and scenario-driven tests. A script is not a recorded demo. The pitch still needs the actual team name, member/institution details, and rehearsal.

## Before external submission

- Complete the unresolved mandatory requirements in `REQUIREMENTS_MATRIX.md`, particularly official Desktop/Android capture gates and physical L1 integration.
- Run and record a consented, representative attack evaluation with fixed thresholds and separate test participants.
- Retain the NASA fixture attribution, official landmark/model provenance, runtime notices and upstream client licenses. Review the reference SBI's inherited bundled JAR terms before distributing its APK.
- Verify a clean extraction/install, model checksums, Python tests, Java checks, and CI results for the submitted commit.
- Record the required demo, play the full export, inspect its start/end, and check that captions and links work. Use a consented subject for live actions; label simulator and fixture footage clearly. A software/simulator recording must disclose its scope and cannot stand in for physical acceptance evidence.
- Add the actual team name/members and institution details to the final private submission material.
- Make the source and artifact URLs accessible to the jury, then verify them in a signed-out session.

The supplied guidelines ask teams to put the other mandatory artifacts in cloud storage and email source/artifact URLs, team name, and problem statement to `decode@mosip.io`. The source repository is public; cloud deliverable uploads, student credential uploads, the submission email, and organizer acknowledgement remain outstanding. See the [item-by-item submission audit](SUBMISSION_STATUS.md).
