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
| `mosip.facepad.<role>.active.timeout_seconds` | Resident `15`; operator/supervisor `20` | Session timeout in seconds (`5` through `60`). Alternate key `mosip.facepad.<role>.timeout_seconds`. |
| `mosip.facepad.<role>.active.max_retries` | `2` | Maximum retry attempts (`0` through `5`). Alternate key `mosip.facepad.<role>.max_retries`. |

Replace `<role>` with `resident`, `operator` or `supervisor`. Booleans are the
literal strings `true` and `false`. Empty values, surrounding whitespace,
non-finite thresholds, out-of-range integer values and malformed booleans fail closed.

The desktop preview receives its operator or supervisor workflow from the
authentication controller. Completed proof is bound to that workflow and the
parsed policy values. Changing role or policy before final acceptance cancels
the proof. Model errors and attack decisions still reject before consumption.
The final JPEG and proof remain single-use. A policy does not supply identity
matching or turn an uncertain passive result into a completed action.

The Android registration/onboarding callback reads the corresponding resident
or operator policy. Its signed active-evidence extension still requires the
existing trusted SBI validation and one-use transaction ledger. The reference
camera app has its own request timeout and two-action implementation. This
change does not add a native settings screen, dynamic custom action pool selection,
localized guidance templates, or cache-update transactions. Android supervisor
UI integration and live synchronization remain unverified.

Verification includes strict parsing, immutable policy values, workflow
separation and changed-policy proof rejection. Real model and controller checks
are recorded separately from injected completion-geometry checks. New source
requires rebuilt platform artifacts before it can be called packaged or tested
on Android.
