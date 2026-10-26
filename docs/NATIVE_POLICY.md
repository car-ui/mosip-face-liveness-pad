# Native cached policy integration

The native adapters read custom extension keys from the host MOSIP clients'
existing configuration caches. Desktop uses `ApplicationContext`; Android uses
`GlobalParamRepository` after the trusted SBI parser and before capture storage.
This change reads configuration. It does not provision a server, change central
settings, or establish that an authenticated online synchronization ran.

Use [the example keys](../config/native-policy.example.properties) as a deployment
reference. They are extension keys introduced by this project, not built-in
MOSIP settings. Missing keys retain the previous native defaults. Explicit
malformed values reject capture. The defaults remain uncalibrated research
settings and are not selected from a measured physical error-rate target.

| Key | Default | Behaviour |
| --- | --- | --- |
| `mosip.facepad.enabled` | `true` | `false` blocks verified capture. It cannot bypass the checkpoint. |
| `mosip.facepad.<role>.passive.threshold` | `0.85` | Finite value from `0.46` through `0.99`. The PAD rejection cutoff stays fixed at `0.45`. |
| `mosip.facepad.<role>.active.enabled` | `true` | Disabling required active checks is invalid. |
| `mosip.facepad.<role>.active.required` | Resident `false`; operator/supervisor `true` | Required for both authentication roles and cannot be disabled there. |
| `mosip.facepad.<role>.active.action_count` | Resident `1`; operator/supervisor `2` | Number of sequential actions required (`1` through `4`). Alternate key `mosip.facepad.<role>.action.count`. |
| `mosip.facepad.<role>.active.challenge_types` | `blink,turn` | Comma-separated allowed native action families: `blink`, `turn`, or both. Alternate key `mosip.facepad.<role>.challenge.types`. |
| `mosip.facepad.<role>.active.timeout_seconds` | Resident `15`; operator/supervisor `20` | Session timeout in seconds (`5` through `60`). Alternate key `mosip.facepad.<role>.timeout_seconds`. |
| `mosip.facepad.<role>.active.max_retries` | `2` | Maximum recovery episodes inside a native frame session (`0` through `5`). Alternate key `mosip.facepad.<role>.max_retries`. |

Replace `<role>` with `resident`, `operator` or `supervisor`. Booleans are the
literal strings `true` and `false`. Empty values, surrounding whitespace,
non-finite thresholds, out-of-range integer values and malformed booleans fail closed.

The desktop preview receives its operator or supervisor workflow from the
authentication controller. Completed proof is bound to that workflow and the
parsed policy values. Changing role or policy before final acceptance cancels
the proof. Model errors and attack decisions still reject before consumption.
The final JPEG and proof remain single-use. A policy does not supply identity
matching or turn an uncertain passive result into a completed action.

The desktop frame session now uses the parsed action count, challenge pool and timeout. The
timeout covers acquisition, preparation and every action; recovery does not
extend it. If an adapter supplies a shorter capture timeout, the shorter limit
wins. Actions alternate between blink and a randomly selected turn, with a
random starting action. Each action requires its own return to neutral.
Selecting only `blink` uses blink for each action; selecting only `turn` uses
turns. Arbitrary action families such as smile or spoken prompts are not
implemented by the native landmark detector.

A recovery episode starts when clear evidence or action progress is interrupted
by face loss, a stream gap or suspect PAD evidence. It clears all action credit
and consumes one retry. Repeated missing frames during that same episode do not
consume additional retries. Zero retries rejects the first interruption after
clear evidence. Confirmed attacks, model errors, invalid sequence and expiry
remain terminal. The limit applies within a session; creating a new capture is
not account-level rate limiting.

The Android registration/onboarding callback reads the corresponding resident
or operator policy. Its signed active-evidence extension still requires the
existing trusted SBI validation and one-use transaction ledger. The checkpoint
requires the signed `actionCount` to be between one and four and at least the
current policy's required count. Evidence version 2 includes the ordered
`actionTypes` actually completed, and every reported action must be in the
current policy's challenge pool. Insufficient counts, unexpected types or
out-of-range values reject before the transaction is consumed. The compatibility
overload uses the default operator policy, which requires two actions.

The reference camera activity accepts a validated requested action count,
`blink`/`turn` pool, timeout and retry limit. Its default is two actions with
both types allowed. `NativePadPolicy.toSbiCustomOptions()` serializes the cached
client policy to four non-sensitive entries in the SBI `customOpts` object;
`CameraSbiRequestPolicy` validates that complete object and maps it to the
private camera activity's typed extras. The SBI specification defines
`customOpts` for configured, documented capture parameters. The gate applies the
policy bounds to the session. Evidence version 2 is minted only
after the native session consumes the exact final JPEG. Its signed payload
includes the ordered action types, session start, effective SBI timeout,
allowed and used retries, action count, completion time, ISO digest, model hashes,
and transaction.
After the existing SBI signature and transaction checks, Android also verifies
that the observed duration fits both the SBI timeout and the current client
timeout, and that retries used fit the current retry limit. Version 1 evidence
is rejected. If the SBI settings differ from the current client policy, its
result fails the client checkpoint.

The pinned Android Registration Client patch now adds a `customOpts` property
to its SBI request DTO and fills it in `BiometricsDetailsApi.rcapture()` for
face/exception-photo requests. It reads the resident or operator policy from
the current global-parameter cache and assigns
`captureRequest.setCustomOpts(policy.toSbiCustomOptions())`. The request options
are still untrusted hints; the signed result is checked against the client's
current policy before storage. The source patch applies to the pinned client
revision, but the updated apps have not been rebuilt here. See the [MOSIP SBI
capture specification](https://github.com/mosip/documentation/blob/1.2.0/docs/id-lifecycle-management/supporting-components/biometrics/sbispec.md)
for the standard `customOpts` request field. It emits
`facePadActionCount`, `facePadTimeoutSeconds`, `facePadMaxRetries`, and
`facePadChallengeTypes`; it carries no subject data, image, transaction secret,
or signing material.
Native pools currently support only blink and turn; additional action families,
localized guidance templates, authenticated cache-update transactions, Android
supervisor UI integration, and live synchronization remain unverified.

Verification includes strict parsing, immutable policy values, workflow
separation and changed-policy proof rejection. Real model and controller checks
are recorded separately from injected completion-geometry checks. New source
requires rebuilt platform artifacts before it can be called packaged or tested
on Android.
