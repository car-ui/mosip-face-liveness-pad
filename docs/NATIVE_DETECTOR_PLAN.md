# Native detector compatibility plan

The pinned desktop OpenCV 4.5.3-4 JAR does not include FaceDetectorYN. Android
uses a newer OpenCV, but a shared implementation must also work on the desktop.
The existing native code performs downscaled frontal Haar detection twice per
action frame, unlike the newer Python detector. A Python success does not
establish the native path's turn tolerance or multiple-face behavior.

Research: the packaged YuNet model has fixed input `[1,3,640,640]` and twelve
outputs at strides 8, 16 and 32. The official [OpenCV 4.11 decoder](https://github.com/opencv/opencv/blob/4.11.0/modules/objdetect/src/face_detect.cpp)
specifies raw BGR input, class/object confidence fusion, box decoding and NMS.
Those contracts allow use of the existing ONNX Runtime dependency without
requiring a new OpenCV Java API. The model's MIT and OpenCV reference licenses
are retained in the project notices.

Execution order:

1. Add a hash-pinned portable Java decoder using the current runtimes. Preserve
   aspect ratio inside its fixed input and map boxes back to source coordinates.
2. Compare real model output with OpenCV Python on identical padded fixture
   inputs, including zero, one and two faces. Validate invalid models/inputs.
   These are detector parity checks, not physical attack accuracy.
3. Only after parity passes, connect the decoder to the native PAD/frame bridge,
   remove the redundant frontal redetection, and package the detector/notice in
   prepared client resources. Keep downstream identity matching and payload
   binding intact.
4. Compile native checks and rebuild affected platform artifacts where tooling
   is available. Record new evidence separately; retain older logs unchanged.
   Do not label an unbuilt APK current or an emulator test physical validation.

The current validated Python local delivery is commit 5834c68. Native work is a
separate local milestone, with no GitHub publication or demo work authorized.

## Local execution record

The portable decoder passed eight real-model cases against OpenCV, including
blank, single-face, two-face and resized inputs. Invalid input and a changed
model were rejected. Actual Java/Python PAD and landmark parity checks passed.
The native action check passed recovery after a suspect observation, sustained
attack rejection, model errors, static geometry, sequence checks, expiry and
one-use exact-JPEG binding. Its geometry is injected and does not measure camera
accuracy. The recorded-photo frame bridge did not complete active verification.

The generated source/resources were synchronized into the three prepared native
checkouts after checking their old source against the previous committed source.
Common and desktop adapter sources compiled against the desktop's resolved
MOSIP classpath using Java 21 with --release 8. This is not a new full reactor
build or a rebuilt Android APK. Existing APKs predate these changes.

Further checks were blocked by host memory and storage exhaustion. The latest
Python run finished with 159 passes and six failures, including explicit OpenCV
and ONNX allocation failures. A repeat failed importing OpenCV with Windows'
paging-file error. Desktop controller checks also failed allocating JVM memory.
These failures are retained on D: and are not counted as passing validation.

No user camera test, phone operation, demo, push or visibility change was done.


Latest validation after resource recovery: all 165 Python tests passed in 16.51
seconds. The completion-transition test now uses explicit controlled inputs,
instead of relying on a real detector and timed gate inside a fixed frame loop.
The native action test also passed after recompiling the final source. Desktop
controller checks subsequently passed on the new detector. Blank ISO captures
were rejected before storage, operator/supervisor rejection made zero matcher
calls, and a completed action double could not override the recorded portrait's
PAD attack verdict. This fixture no longer exercises positive matcher acceptance.
See native-yunet-controller-check.json. Earlier resource failures remain in logs;
Android rebuilds, physical attack accuracy and live client UI remain unverified.
