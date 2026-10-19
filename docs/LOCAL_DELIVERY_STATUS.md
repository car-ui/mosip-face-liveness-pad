# Local delivery status

19 October 2026. The user requested completion work with GitHub publication and
the demonstration left out. New changes are saved locally. Existing remote
visibility and published refs are not changed by this delivery.

## Completed in this pass

- Both Python interfaces now show completed-action counts instead of a
  per-action percentage that looked like overall verification progress.
- PAD-related restarts explicitly clear action credit, create an audit event
  and hold a short recovery interval before new instructions. PAD continues
  running during recovery. The policy does not retain invalid action credit.
- Main action instructions remain stable; browser secondary feedback has reading
  time. Camera/model scores remain separate from completed-action progress.
- Numeric score observations survive audit filtering under explicit numeric
  field names; raw image/frame buffers remain blocked.
- Optional validated offline policy files work in the desktop and service.
  Authenticated API changes are atomically saved before the running policy is
  changed. An example configuration and failure-path tests are included.
- The browser/service default trial deadline is 45 seconds to allow more room
  for two actions and preparation. Explicit request bounds remain 2 to 60 seconds.
- Actual laptop observations are summarized without images or subject IDs in
  `physical-webcam-observations.json`. Of three recorded trials, two ended in
  accepted prototype capture with completed actions; one was rejected. Some
  sequences restarted. This is not a population accuracy estimate.

## Validation

The workspace suite passed 165 tests in 31.71 seconds. Console JavaScript passed
Node syntax checking. A rendered static-fixture UI was visually inspected with
one of two actions completed. The native evidence validator passed 24 checksums
and matched six Android measurement logs. That last check establishes retained
evidence integrity, not new native execution or hardware validation. Fresh
committed-source package verification is performed at delivery.

## Requirements that remain genuinely open

The remaining gaps cannot be marked complete by adding prototype features:

1. Independent live and physical print/display/mask trials, with frozen settings,
   held-out subjects/sources, attack-group errors and nonresponse counts. There
   is still an apparent live-person rejection in the observed laptop trials.
2. A complete official desktop/Android client camera-to-acceptance run, including
   real identity matching where required. The accepted Python prototype trial
   does not establish official operator or supervisor authentication.
3. Physical Android and real L1/multiple-vendor integrations, production device
   certificate trust and actual vendor streaming/format compatibility. Current
   signed acceptance tests use declared crypto/repository fixtures.
4. Native platform adoption and validation of newer prototype detector/session
   policies, and integration with MOSIP's configuration framework. The Python
   policy-file implementation does not complete those native software tasks.
   Inspection confirmed the pinned desktop OpenCV 4.5.3 JAR does not contain
   `FaceDetectorYN`. The Python YuNet adapter therefore cannot be copied into
   the native client. Adopting it requires a native decoder or a validated
   dependency upgrade and rebuilt platform artifacts.

The source package, regression checks and research evidence are local reviewable
deliverables. The full mandatory hackathon scope is not declared complete.
Publication, repository visibility changes, a public release, demo recording and
external submission are excluded from this pass.

## Subsequent native milestone

Portable YuNet detection and bounded session PAD observations are now connected
in native source. The PAD decision and action landmark crop share the same face
box. All platform resource preparation includes the detector and its MIT notice.
See NATIVE_DETECTOR_PLAN.md for executed checks and remaining build limitations.
Native configuration framework adoption, APK rebuilds and physical native tests
remain open. Retained APKs must not be described as containing this new source.

The later validation attempt hit host resource exhaustion. Its result was 159
passes and six failures, followed by an OpenCV import failure from an exhausted
Windows paging file. The earlier 165-pass result remains historical evidence,
not a claim that this later run passed. Desktop controller validation was also
blocked by memory allocation. New source is saved locally with these limits.

To preserve disk headroom, the project model directory and Git storage now use
Windows directory junctions to D:/CodexWork/native-face-pad-20261018/workspace-models
and workspace-git. Paths in the checkout still work. The unused broken .venv was
preserved on D: as preserved-broken-workspace-venv. The supported launcher uses
the separate working D: Python environment. Repository connectivity was checked.
