# Native client integration contract

The supplied prototype contains a Python research service and independent Java components. It does not contain verified changes to the official MOSIP Registration Clients. The following contract identifies the implementation and evidence needed to connect them without bypassing liveness.

## Verified components

`MosipLivenessDeviceService` is a Java 8-compatible loopback HTTP adapter with workflow validation, bearer authentication, bounded reads, and timeouts. It returns unparsed JSON. Its demo performs discovery only and does not print biometric payloads.

`NativeCaptureGate` is a portable Java component that rejects wrong sessions, repeated frame sequences, missed deadlines, failed quality, unavailable PAD, and attack verdicts. It counts distinct challenge instance identifiers and binds an accepted payload to a SHA-256 digest. The exact bytes can be consumed only once. It trusts its caller to provide real inference results and system-issued challenge instance IDs. It does not verify camera attestation or signatures, generate actions, infer faces, or match identity.

The standalone Java test exercises these properties. Compiling Java code for Java 8 does not establish a working Android APK or a successful MOSIP registration.

## Desktop insertion points

1. Pin an official Registration Client version and record its commit.
2. Identify the supported vendor SBI/device streaming API. Decode only documented frame formats and verify required device signatures.
3. Run the inference adapter on fresh frames with bounded queues. Keep inference off the UI thread and measure frame latency.
4. Bind each resident/operator/supervisor session to its workflow policy and current candidate capture.
5. Place the acceptance gate at the final face-capture acceptance and authentication completion points. Manual capture, retries, exceptions, and supervisor recovery must not bypass it.
6. Deliver the exact verified image to the client's existing format encoder. Perform normal identity matching for authentication.
7. Prove rejection in the actual client UI and verify that the registration packet or authenticated state was not produced.

## Android insertion points

MOSIP's Android documentation describes invoking the external SBI application for biometric capture, then returning biometric data to the Registration Client. Receiving a final capture URI does not automatically grant access to continuous face frames. Source: [official Android client features](https://docs.mosip.io/1.2.0/id-lifecycle-management/identity-issuance/android-registration-client/overview/features).

The device/SBI vendor must provide a supported streaming or periodic frame interface, or liveness must run inside the capture-owning application with a verifiable result bound to its signed capture. Do not treat a separate webcam session as proof about a different final SBI image.

Deploy the actual PAD and action models with Android-compatible runtimes. Convert Camera/SBI pixel formats deliberately, preserve rotation/mirroring conventions, and compare preprocessing with the desktop reference. Run inference on a bounded worker and measure target-device p50/p95 latency, peak RAM, thermal behavior, and recovery after backgrounding. GPU/NPU provider availability must be measured rather than inferred from a provider list on a desktop.

## Acceptance matrix still required

For each of resident, operator, and supervisor on both Desktop and Android: demonstrate passive success where permitted, uncertain-to-active escalation, valid and wrong actions, attack during active verification, face substitution/loss, timeout, maximum retries, offline operation, device disconnect, and rejection before final client acceptance. Repeat across supported L0 and real L1 devices. Record app/model/device versions and the corresponding audit session.

Physical L1 devices, deployment credentials, institution IDs, and consented human test data are external requirements. They are not supplied by writing an adapter or passing synthetic tests.
