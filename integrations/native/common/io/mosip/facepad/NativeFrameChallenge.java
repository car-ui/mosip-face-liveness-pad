package io.mosip.facepad;

import java.io.IOException;
import java.nio.file.Path;
import org.opencv.core.*;
import org.opencv.imgcodecs.Imgcodecs;
import org.opencv.imgproc.Imgproc;
import org.opencv.objdetect.CascadeClassifier;

/** Trusted decoded-frame bridge. This is not an SBI signature/transaction validator. */
public final class NativeFrameChallenge {
    private final NativePadEngine pad;
    private final NativeLandmarkEngine landmarks;
    private final CascadeClassifier detector;
    private final NativeActiveSession session;
    private long sequence;

    public NativeFrameChallenge(NativePadEngine pad, NativeLandmarkEngine landmarks, Path cascade,
            long timeoutMillis) throws IOException {
        if (pad == null || landmarks == null) throw new IOException("Frame models unavailable");
        this.pad = pad; this.landmarks = landmarks;
        detector = new CascadeClassifier(cascade.toString());
        if (detector.empty()) throw new IOException("Face detector unavailable");
        session = new NativeActiveSession(timeoutMillis);
    }

    public synchronized NativeActiveSession.State observe(byte[] jpeg) throws Exception {
        if (session.state() != NativeActiveSession.State.VERIFYING) return session.state();
        if (jpeg == null || jpeg.length < 4 || jpeg.length > BoundedMjpegReader.MAX_FRAME_BYTES) {
            session.invalidateFrame(); throw new IOException("Invalid challenge frame size");
        }
        MatOfByte encoded = new MatOfByte(jpeg);
        Mat image = null, small = new Mat(), gray = new Mat();
        MatOfRect faces = new MatOfRect();
        try {
            image = Imgcodecs.imdecode(encoded, Imgcodecs.IMREAD_COLOR);
            NativePadEngine.Decision decision = pad.evaluateBgr(image, true);
            if ("NO_FACE".equals(decision.reason) || "MULTIPLE_FACES".equals(decision.reason)
                    || "INVALID_IMAGE".equals(decision.reason)) {
                session.invalidateFrame(); return session.state();
            }
            if ("PRESENTATION_ATTACK".equals(decision.reason) || "MODEL_ERROR".equals(decision.reason))
                return session.observe(++sequence, null, decision, jpeg);
            Imgproc.resize(image, small, new Size(), .5, .5, Imgproc.INTER_LINEAR);
            Imgproc.cvtColor(small, gray, Imgproc.COLOR_BGR2GRAY);
            detector.detectMultiScale(gray, faces, 1.15, 4, 0, new Size(30,30), new Size());
            Rect[] found = faces.toArray();
            if (found.length != 1) { session.invalidateFrame(); return session.state(); }
            Rect face = new Rect(found[0].x * 2, found[0].y * 2, found[0].width * 2, found[0].height * 2);
            NativeLandmarkEngine.Observation observation;
            try { observation = landmarks.observe(image, face); }
            catch (IOException missing) { session.invalidateFrame(); return session.state(); }
            return session.observe(++sequence, observation, decision, jpeg);
        } catch (Exception | LinkageError failure) {
            session.invalidateFrame(); throw failure;
        } finally {
            encoded.release(); if (image != null) image.release(); small.release(); gray.release(); faces.release();
        }
    }

    public synchronized String prompt() { return session.prompt(); }
    public synchronized NativeActiveSession.State state() { return session.state(); }
    public synchronized boolean consume(byte[] exactFrameJpeg) throws Exception { return session.consume(exactFrameJpeg); }
    public synchronized void invalidateFrame() { session.invalidateFrame(); }
    public synchronized void cancel() { session.cancel(); }
}
