# Remaining acceptance work and time estimate

Updated 26 October 2026. The project now has 16 of 27 requirements implemented
at prototype scope. Eleven remain partial because their acceptance evidence
requires native platform builds, physical devices, consented participants,
vendor SDKs or a real submission. Prototype code and physical acceptance are
tracked separately so a simulator result is not presented as a hardware result.

## The nine remaining items that do not require L0/L1 devices

These can be pursued with ordinary cameras, Android phones, test accounts,
datasets and participants. They still cannot be accepted from source code or
simulator results alone. A focused local run on 23 October passed 26 evaluation,
manifest-integrity, interoperability and usability-protocol tests. The
interoperability CLI returned valid for the webcam contract, mock adapter and
two simulated vendors; it did not open a camera or test physical vendors. This
workspace has no PAD video dataset, Flutter/Android SDK, `adb`, official test
identities/environment, or completed participant-study results. The cached
Gradle distributions do not include an Android SDK.

| Criterion | What can be reused now | Evidence still needed |
| --- | --- | --- |
| Mandatory 2: passive liveness | Dataset evaluator, development-only threshold selector, split and reporting protocol | Authorized, consented development and held-out bona-fide/attack clips; frozen model and threshold; actual report with class counts and nonresponses. |
| Mandatory 3: presentation-attack detection | Fail-closed PAD logic, per-clip evaluator and attack-group reporting | Physical print/replay/mask/injection trials as applicable, or an authorized representative dataset; the device need not be L0/L1. |
| Mandatory 5: resident registration | Patched client and reference SBI source; existing earlier emulator evidence | Current APK build, camera-enabled client-to-SBI-to-storage run, test resident and retained logs. |
| Mandatory 6: operator authentication | Native checkpoint and policy source; desktop operator and face-login paths freshly compile through the patched five-module reactor | Current client/SBI package, live action flow, test operator, and successful or rejected match result through the real test environment. |
| Mandatory 7: supervisor authentication | Supervisor policy/checkpoint source; desktop EOD and role-specific face-login paths freshly compile through the patched five-module reactor | Same live environment with a supervisor test identity, including override/audit behavior. |
| Mandatory 8: configuration | Cached-policy serializer, strict SBI parser, Java handoff checks, exact-revision patch preparation | Build both current Android apps, then change policy and demonstrate the client accepts matching evidence and rejects stale/looser evidence end to end. |
| Mandatory 10: UI/UX | Responsive console, accessibility behavior and ready-to-run study protocol | Consent and run the protocol with representative participants on the target screens and camera; record outcomes and retest fixes. |
| Bonus: low-resource Android | Earlier one-CPU emulator benchmark and instrumentation | Rebuild current source and measure full workflow, latency, memory, energy and thermals on a representative physical low-resource Android phone. |
| Bonus: hardware acceleration | CPU/Azure parity harness and provider placement report | Run CPU and a supported Android GPU/NPU/NNAPI provider on a physical phone and verify actual node placement and numerical parity. |

The only two criteria directly requiring real L0/L1 vendor devices are mandatory
1 and the multiple-vendor good-to-have item. The nine rows above have separate
dependencies; the absence of L0/L1 hardware does not remove those dependencies.

## Remaining tasks

| Task | Work left | Active effort after prerequisites are ready | Main dependency |
| --- | --- | ---: | --- |
| Mandatory 1: L0/L1 device integration | Implement and verify vendor adapters, signed frame or capture validation, device format handling and recovery against actual hardware. | 5-10 working days per vendor | Vendor SDKs, two devices, certificates and vendor documentation. Procurement and access can add weeks. |
| Mandatory 2: Passive liveness | Collect separate development and held-out clips, choose a threshold on development data, then report APCER/BPCER and nonresponses on test data. | 5-10 working days | Consented participants, attack instruments, representative cameras and lighting. |
| Mandatory 3: Presentation attack detection | Run the declared print, screen, mask and injection matrix; retain group outcomes and a reproducible report. | 3-7 working days | Same data collection setup; independent evaluation adds additional time. |
| Mandatory 5: Resident registration | Rebuild patched Android and Desktop clients, capture from a live camera, verify the normal registration storage and packet path, and retain logs. | 2-4 working days | Build toolchains, physical Android device, working SBI and registration environment. |
| Mandatory 6: Operator authentication | Exercise the patched preview and capture path with live actions, trusted SBI result, and successful identity match. | 2-4 working days | Same integration environment plus a valid operator test identity. |
| Mandatory 7: Supervisor authentication | Verify the live supervisor path, policy, audit and override controls from capture through match. | 1-3 working days | Supervisor account, integrated client and trusted SBI. |
| Mandatory 8: Configuration | The pinned client's outbound RCAPTURE policy, conversion from standard SBI `customOpts` object to the reference DAO's list DTO, and strict camera-side parsing are implemented and apply to both exact source revisions. Rebuild both apps and verify stricter policy updates and rejection cases end to end. | 0.5-1 working day | Android SDK/build environment and SBI/device test setup. |
| Mandatory 10: UI/UX | The task protocol and review gates are ready. Run task-based accessibility and usability sessions on official Desktop and Android screens; fix and recheck discovered issues. | 3-5 working days | Representative users, screen readers and physical cameras. |
| Good-to-have: Multiple vendors | Connect and exercise at least two real vendor integrations across the documented format/security matrix. | 5-10 working days after the first adapter | Vendor SDKs and devices; this overlaps with Mandatory 1. |
| Bonus: Low-resource Android | Rebuild current sources and measure full capture latency, RAM, energy and thermal behavior on representative low-resource phones. | 2-4 working days | Physical ARM64 devices and repeatable measurement setup. |
| Bonus: Hardware acceleration | The host provider harness ran with exact CPU/Azure output parity, but profiling assigned all nodes to CPU. Measure supported Android GPU/NPU/NNAPI execution and numerical parity against CPU on target devices. | 2-4 working days | A phone with a supported provider and compatible runtime. |

The new interoperability framework is implemented at prototype scope: it checks
capability consistency for the webcam contract, simulator and two simulated
vendor adapters. Real vendor interoperability remains in the rows above.

## Overall estimate

With the required devices, SDKs, participants, certificates and client
environment available at the start, expect **15-25 working days** of remaining
work, or about **3-5 calendar weeks** for a small team. Some data collection,
client integration and device profiling can run in parallel. If vendor devices
or SDKs must be acquired, plan **4-8 weeks or longer**. Formal ISO/IEC 30107
independent certification is a separate laboratory project and may take
substantially longer.

Submission closeout is separate from the 27-item implementation matrix. The
supplied guide treats a 2-5 minute demo video as optional. Add the real
team/institution details to private submission materials and verify artifact
links. If the team chooses to include a video, allow another half to one
working day to record and review it once the demo setup is ready.

The source-only integration and packaging work is complete. The latest pinned
Desktop patch applies cleanly and the five-module reactor compiles locally with
Maven tests skipped; a JDK 11 build, current native runtime harness and live
camera/UI run remain open. Remaining local release work is to build the
Android targets, resolve any integration failures, and refresh signed or
reproducible build evidence. Allow **1-2 working days** once the Android
SDK/Gradle toolchain and test setup are available. This workspace has no
system Gradle, Android SDK or `adb`; the temporary Maven distribution and
locked Python dependencies used for verification are under ignored `tmp/`.
The retained APKs still validate an earlier code milestone and do not include
the latest evidence-v2 or camera-policy changes.

These are engineering estimates, not a guaranteed delivery date. The largest
schedule risks are vendor access, test-participant scheduling, official client
environment setup, and failures that appear only on physical hardware.
