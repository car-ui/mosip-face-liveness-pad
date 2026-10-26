# Native workflow usability and accessibility study

This protocol is ready to run against the packaged Desktop and Android clients.
It records interaction quality, not PAD accuracy or security acceptance. A
facilitator must use the exact client build and device being evaluated.

## Prepare the session

- Recruit consenting adults familiar with basic camera use. Include participants
  who use screen readers, magnification, keyboard-only navigation, or other
  relevant accessibility features when available.
- Use test identities and a non-production registration environment. Never
  collect a national ID, real registration packet, production credential, or
  biometric image for this study.
- Record client/build hashes, OS and device model, camera, locale, display size,
  assistive technology, policy version, facilitator, and date.
- Explain the camera purpose, whether frames are processed locally, what is
  retained, and how to stop. Obtain consent before starting. Do not record
  video/audio by default; take anonymous task notes only.
- Test each resident, operator, and supervisor flow with the same declared
  configuration. Include a physical camera on the target device; simulators are
  useful for layout checks but cannot establish camera usability.

## Participant tasks

Give each task without coaching the participant through the screen. The
facilitator may repeat the task text once and records any additional help.

1. Start resident face capture and position the face using only the guidance.
2. Complete a randomly selected action prompt and explain how the participant
   knows the action succeeded.
3. Deliberately miss one action, then recover using the displayed retry guidance.
4. Cancel capture and describe whether the participant expects a biometric to
   have been stored.
5. On operator and supervisor screens, start face authentication, follow the
   action prompt, and explain the displayed result without using debug details.
6. Repeat the relevant tasks with keyboard-only controls or the participant's
   normal screen reader/magnification setup.

Use only intended test procedures for missed actions and cancellation. Never
ask a participant to defeat PAD, expose a real identity, or change a security
threshold.

## Record per-task outcomes

For each participant and task, record only an anonymous study code and:

- task completed: yes/no;
- elapsed time in seconds;
- number of facilitator prompts;
- visible or spoken guidance understood: yes/no;
- error, retry, cancellation, or unexpected capture behavior;
- whether the participant correctly understood the final outcome;
- short anonymous observation and severity (critical, major, minor).

After each platform, ask participants to rate these statements from 1 (strongly
disagree) to 5 (strongly agree):

1. I knew what the screen expected me to do.
2. The face-positioning guidance was easy to follow.
3. The action prompts were clear and easy to hear or read.
4. I understood when liveness checking was in progress.
5. I understood why a retry or failure occurred.
6. I felt in control of starting and stopping camera capture.
7. The interface worked with my usual accessibility settings.

## Prototype review gates

These are project review gates, not MOSIP certification or accessibility
standards:

- Any accepted capture after cancel, timeout, missing-face, or failed challenge
  is a critical defect and blocks the build.
- At least 90% of participants should finish each required task without
  facilitator assistance before the flow is presented as usable.
- No participant should be left unsure whether capture was cancelled, accepted,
  or failed; unclear outcomes are major issues to fix and retest.
- Screen-reader users must receive the current prompt and a change in status;
  keyboard-only users must be able to start, retry, and cancel without a mouse.
- Re-run every task affected by a fix. Report participant count and platform;
  do not generalize a small usability sample to the broader population.

## Session report template

```text
Build hash:
Platform / OS / device:
Policy version:
Assistive technology tested:
Participants (anonymous count):
Tasks completed without help / total:
Median task time by task:
Critical issues:
Major issues:
Minor issues:
Fixes and retest results:
Limitations:
```

No completed human usability study is currently included in this repository.
The protocol does not substitute for participant results.
