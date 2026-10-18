# Native active-challenge work

The native Java code now runs the same FaceMesh V2 landmark submodel used by the inherited MediaPipe bundle. It also contains a session action state machine and a decoded-frame bridge. The action state machine and decoded-frame bridge are connected to the desktop operator/supervisor authentication preview. The actual controller accepts an exact completed-session image and rejects a different image in controlled tests. Those tests use injected action geometry and an identity matcher double. Successful authentication with a live person remains unverified. A reference Android camera SBI now evaluates its own Camera2 frames and places exact-ISO active evidence inside its signed capture payload. The client connection passes controlled parser/API tests; live actions and production PKI remain unverified.

## Model and geometry

The original bundle matches Google's version 1 float16 download. Its official guide links model cards that identify Apache License 2.0 for the detector, FaceMesh V2 and blendshape models. The repository retains that license and component checksums. The native engine uses only the FaceMesh V2 submodel, converted to ONNX without training. Its input is RGB float values divided by 255, with shape 1 by 256 by 256 by 3, as specified in the original TFLite metadata. The Java adapter resizes a square crop with 1.5 times the detected face size. It rejects a crop that would extend outside the image. Rotation alignment and tracking still need work.

The engine reads 478 three-dimensional landmarks and applies sigmoid once to the face-presence logit. It does not treat the bundle's other scalar output as face presence. The eye aspect ratio measures vertical eye opening relative to horizontal eye width. The turn ratio measures the nose's horizontal displacement between the outer eye corners. It is a geometric ratio, not a calibrated head angle in degrees.

The converted ONNX model passed 24 comparisons with TFLite across eight tensors, including a recorded photograph crop. The largest absolute output difference was 0.00098. Java ONNX inference matched Python ONNX inference on the tested input. Blank presence, invalid inputs, clipped crops and model tampering reject. These checks establish conversion and adapter behavior, not action detection accuracy.

The conversion script also passed a separate reproduction run. Its serialized graph checksum differed, so the native engine pins the exact packaged ONNX file. A future export must be checked and its checksum reviewed before replacing that model. Conversion tooling is isolated from the runtime dependency lock.

## Action sequence

`NativeActiveSession` selects a blink and one randomly directed head turn, in random order. Every action starts from a stable neutral face with both eyes open. A blink requires closed eyes followed by open eyes. A turn requires motion in the requested preview direction followed by a return to neutral. Minimum frame counts and time holds prevent one frame from completing an action. The current thresholds are research settings and have not been calibrated on people.

Face loss or a gap of more than one second clears all action progress. A duplicate or out-of-order frame sequence, PAD attack, processing failure or expiry cannot produce a completed result. Completed evidence is bound to the SHA-256 of the final frame's exact JPEG bytes and can be consumed once, within two seconds of completion. A different final capture fails. Stopping or replacing the stream cancels its evidence. This byte binding does not replace SBI signature, transaction or device attestation validation.

`NativeFrameChallenge` derives the PAD and landmark observations from the same decoded frame. Twelve repeated JPEGs of the attributed static NASA photograph do not complete the sequence under the actual models. Separate injected-geometry checks exercise successful state transitions, resets, expiry and candidate binding. Injected geometry is not a live action test.

## Remaining client connection

The native preparer packages the models, manifests and notices and installs the Java classes into both pinned clients. Android instrumentation executes the landmark model on the recorded fixture. Android and desktop paths without connected active evidence continue to reject required active captures.

In the desktop `OperatorAuthentication.fxml` flow, Scan now starts the active preview. The instruction label receives session prompts on the JavaFX thread. Completion starts the existing capture/authentication task, which passes the same stream-session object to the checkpoint. Only a JPEG candidate whose exact bytes match that completed session can reach the existing identity matcher through this new path. Other authentication screens and onboarding still use the checkpoint without active proof and remain blocked.

The upstream test encoder convenience method marks supplied JPEG bytes as JPEG2000. The portrait test corrects that format tag before checking byte-preserving binding. Historical blank-ISO checks used that convenience format and are synthetic control-flow evidence, not format-conformance evidence.

 Android's SBI app owns its camera session, so the client alone cannot infer current actions from a completed capture URI. The patched reference camera SBI supplies a custom signed extension with an ISO digest, both model hashes, current transaction and completion time. The patched Android client validates these after its existing trusted SBI parser and consumes the transaction once in persistent storage. See [camera SBI details and test scope](CAMERA_SBI_INTEGRATION.md). If the SBI encodes its final image differently from the preview, comparing JPEG bytes will fail safely. JPEG2000 cannot use the JPEG-bound active proof path; weakening the comparison to an unauthenticated similarity score is not a complete binding solution.

Native successful operator/supervisor authentication, live action accuracy, full client camera/UI workflows and physical attack evaluation remain pending. No camera or physical person is represented by the recorded photograph or injected geometry.
