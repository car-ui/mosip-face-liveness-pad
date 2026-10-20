# Native policy enforcement, 20 October

The freshly fetched starting point was `a4d851c`. Its native configuration parser
accepted action count, timeout and retry settings, but the frame challenge still
constructed a fixed two-action session. Desktop also supplied a fixed 30-second
timeout. Android evidence accepted a fixed two-action proof without consulting
the current policy's count.

The frame challenge now applies the policy count, timeout and recovery limit.
Desktop supplies its configured timeout. An adapter's shorter timeout remains a
cap. Recovery clears action credit and consumes one attempt per interruption,
without charging each consecutive missing frame. Confirmed attacks and model
errors remain terminal. Android requires signed action counts between one and
four that meet the current minimum before writing the one-use ledger.

Current checks include 199 passing Python tests in 28.86 seconds, native action
and policy control-flow checks, a successful Java 11 five-module desktop build,
and both actual desktop controller and JavaFX preview checks. Android's evidence
verifier also passed a host harness using real JSON and stub Android storage and
DTO classes. That harness is not Android instrumentation.

The action checks cover one, three and four actions, expiry with an incomplete
sequence, zero recovery attempts and one recovery episode followed by repeated
missing frames. Existing one-use proof, PAD veto, sequence, clock and exact-image
checks still pass. These use injected geometry rather than measured human
action recognition. Retained summaries are in
`integrations/native/evidence/policy-session-20261020`.

Android instrumentation source now contains 17 client tests. New APK builds and
instrumentation results must be recorded separately after they finish. Earlier
19 October APKs do not contain this enforcement change.

The reference camera still supplies two-action version 1 evidence. It can satisfy
client minima of one or two, and rejects at the client if three or four are
required. That proof does not carry session start time, retries or a complete
policy snapshot. Enforcing the client's timeout and retry values across the
Android/SBI boundary still needs an authenticated request and signed response
contract. This milestone does not complete that contract, native action pools,
guidance configuration or online synchronization.

Physical attack evaluation, real L1/vendor integration, production trust and live
official-client camera-to-storage and identity-matching workflows remain open.
Publication is authorized; demo recording and visibility changes are excluded.
