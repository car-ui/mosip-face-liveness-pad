# Resume checkpoint

The current branch is `new/hackathon-quality`. Resolve its exact commit with
`git rev-parse HEAD`; the predecessor was `30686fb13db650fb4a58dbfcc90dc2a8a3c8e38d`.
Push to both `main` and `new/hackathon-quality`, with `[skip ci]` in commit messages.
Do not run GitHub Actions because the user's allowance is exhausted.

Read `RELIABILITY_PLAN.md` before making more inference changes. The user asked
for research first, a written plan second, then implementation. That sequence
has been followed for the session evidence gate and optional MN3 profile.

Protected: do not add or change the untracked root `ps4.pdf` and
`evaluation criteria.pdf`. Do not publish the user's screenshots, camera images
or private diagnostic files. No physical-trial images were saved by diagnostics.

Validation: 151 tests passed; simulator UI settling/exit smoke passed. Previous
141-test source archive also passed after extraction. The new model uses a
verified official download and retained MIT license. Models remain uncalibrated
for this camera and population. There is still no completed physical native
MOSIP client demonstration.

Local artifacts/runtime: `D:\CodexWork\native-face-pad-20261018` and Python
`D:\CodexWork\face-pad-clean-20261018\Scripts\python.exe`. Keep installs,
archives and temporary files on D because C has little free space. The launcher
is `artifacts\START-LAPTOP-PHYSICAL-TRIAL.cmd`; verify it points to a clean
extraction of the latest committed release rather than a patched old extraction.

Next evidence work: evaluate labelled independent live/physical-attack sessions
using the fixed model and complete session policy. Do not lower thresholds,
switch models based on higher live scores, or call score-double tests physical
accuracy. The user does not want another request to retry while the software is
being changed. Native Java/Android policy changes require separate work and tests.

Latest local work adds action-count progress, explicit restart recovery, numeric score audit fields and validated offline policy persistence. The user now excludes GitHub publication and the demo. Do not push new commits or change visibility. See LOCAL_DELIVERY_STATUS.md and the retained physical webcam observations. The remote baseline remains 2ac8c92.
