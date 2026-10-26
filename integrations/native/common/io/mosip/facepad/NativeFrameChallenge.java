package io.mosip.facepad;

import java.io.IOException;
import java.nio.file.Path;
import org.opencv.core.*;
import org.opencv.imgcodecs.Imgcodecs;

/** Trusted decoded-frame bridge. This is not an SBI signature/transaction validator. */
public final class NativeFrameChallenge {
    private final NativePadEngine pad;
    private final NativeLandmarkEngine landmarks;
    private final NativeActiveSession session;
    private final NativePadPolicy policy;
    private long sequence;

    public NativeFrameChallenge(NativePadEngine pad, NativeLandmarkEngine landmarks, Path cascade,
            long timeoutMillis) throws IOException {
        this(pad,landmarks,timeoutMillis);
    }

    public NativeFrameChallenge(NativePadEngine pad, NativeLandmarkEngine landmarks,
            long timeoutMillis) throws IOException {
        this(pad,landmarks,timeoutMillis,NativePadPolicy.defaults(NativePadPolicy.Workflow.OPERATOR));
    }

    public NativeFrameChallenge(NativePadEngine pad, NativeLandmarkEngine landmarks,
            long timeoutMillis,NativePadPolicy policy) throws IOException {
        if (pad == null || landmarks == null) throw new IOException("Frame models unavailable");
        if (policy == null || !policy.enabled || !policy.activeEnabled || !policy.activeRequired)
            throw new IOException("Active verification policy unavailable");
        this.pad = pad; this.landmarks = landmarks;
        this.policy = policy;
        session = new NativeActiveSession(timeoutMillis, policy);
    }

    public synchronized NativeActiveSession.State observe(byte[] jpeg) throws Exception {
        if (session.state() != NativeActiveSession.State.VERIFYING) return session.state();
        if (jpeg == null || jpeg.length < 4 || jpeg.length > BoundedMjpegReader.MAX_FRAME_BYTES) {
            session.invalidateFrame(); throw new IOException("Invalid challenge frame size");
        }
        try { BoundedImage.requireJpeg(jpeg); }
        catch (IOException invalid) { session.invalidateFrame(); throw invalid; }
        MatOfByte encoded = new MatOfByte(jpeg);
        Mat image = null;
        try {
            image = Imgcodecs.imdecode(encoded, Imgcodecs.IMREAD_COLOR);
            NativePadEngine.Decision decision = pad.evaluateBgr(image, policy);
            if ("NO_FACE".equals(decision.reason) || "MULTIPLE_FACES".equals(decision.reason)
                    || "INVALID_IMAGE".equals(decision.reason)) {
                session.invalidateFrame(); return session.state();
            }
            if ("PRESENTATION_ATTACK".equals(decision.reason) || "MODEL_ERROR".equals(decision.reason))
                return session.observe(++sequence, null, decision, jpeg);
            Rect face = decision.faceBox;
            if (face == null) { session.invalidateFrame(); return session.state(); }
            NativeLandmarkEngine.Observation observation;
            try { observation = landmarks.observe(image, face); }
            catch (IOException missing) { session.invalidateFrame(); return session.state(); }
            return session.observe(++sequence, observation, decision, jpeg);
        } catch (Exception | LinkageError failure) {
            session.invalidateFrame(); throw failure;
        } finally {
            encoded.release(); if (image != null) image.release();
        }
    }

    public synchronized String prompt() {
        return "Actions " + session.completedActions() + "/" + session.requiredActions() + ". " + session.prompt();
    }
    public synchronized NativeActiveSession.State state() { return session.state(); }
    public synchronized boolean consume(byte[] exactFrameJpeg) throws Exception { return session.consume(exactFrameJpeg); }
    public synchronized NativeActiveSession.Attestation consumeAndAttest(byte[] exactFrameJpeg) throws Exception {
        return session.consumeAndAttest(exactFrameJpeg);
    }
    public synchronized boolean consume(byte[] exactFrameJpeg,NativePadPolicy expectedPolicy) throws Exception {
        if (!policy.sameAs(expectedPolicy)) { session.cancel(); return false; }
        return session.consume(exactFrameJpeg);
    }
    public synchronized void invalidateFrame() { session.invalidateFrame(); }
    public synchronized void cancel() { session.cancel(); }
}
