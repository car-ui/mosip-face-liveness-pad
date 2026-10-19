package io.mosip.facepad;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import java.io.IOException;
import java.nio.FloatBuffer;
import java.nio.file.Path;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Collections;
import org.opencv.core.*;
import org.opencv.imgcodecs.Imgcodecs;
import org.opencv.imgproc.Imgproc;

/** Offline passive checkpoint. A single image cannot supply active challenge evidence. */
public final class NativePadEngine implements AutoCloseable {
    public static final String MODEL_SHA256 = "5281b4a621b1a2a7570d88bc3a37ac5273ab3082b61d1e284b9847660909cbef";
    private final OrtEnvironment environment = OrtEnvironment.getEnvironment();
    private final OrtSession session;
    private final NativeYuNet detector;
    private final String inputName;
    private final int inferenceThreads;

    public static final class Decision {
        public final boolean accepted;
        public final String reason;
        public final double score;
        final Rect faceBox;
        public Decision(boolean accepted, String reason, double score) {
            this(accepted,reason,score,null);
        }
        Decision(boolean accepted, String reason, double score, Rect faceBox) {
            this.accepted = accepted; this.reason = reason; this.score = score; this.faceBox = faceBox;
        }
    }

    public NativePadEngine(byte[] model, Path cascadePath) throws Exception {
        this(model,Files.readAllBytes(cascadePath.resolveSibling("face_detection_yunet_2023mar.onnx")));
    }

    public NativePadEngine(byte[] model, byte[] detectorModel) throws Exception {
        if (!MODEL_SHA256.equals(sha256(model))) throw new IOException("PAD model checksum mismatch");
        NativeYuNet loadedDetector = new NativeYuNet(detectorModel);
        inferenceThreads = Math.max(1, Math.min(2, Runtime.getRuntime().availableProcessors()));
        try (OrtSession.SessionOptions options = new OrtSession.SessionOptions()) {
            options.setIntraOpNumThreads(inferenceThreads);
            options.setInterOpNumThreads(1);
            session = environment.createSession(model, options);
        } catch (Exception | LinkageError failure) {
            loadedDetector.close(); throw failure;
        }
        detector = loadedDetector;
        inputName = session.getInputNames().iterator().next();
    }

    public int getInferenceThreads() { return inferenceThreads; }

    public static String sha256(byte[] bytes) throws Exception {
        StringBuilder result = new StringBuilder();
        for (byte value : MessageDigest.getInstance("SHA-256").digest(bytes))
            result.append(String.format("%02x", value & 255));
        return result.toString();
    }

    public synchronized Decision evaluateEncoded(byte[] encoded, boolean activeRequired) throws Exception {
        return evaluateEncoded(encoded,NativePadPolicy.defaults(activeRequired ? NativePadPolicy.Workflow.OPERATOR : NativePadPolicy.Workflow.RESIDENT));
    }

    public synchronized Decision evaluateEncoded(byte[] encoded, NativePadPolicy policy) throws Exception {
        if (policy == null || !policy.enabled) return new Decision(false,"LIVENESS_DISABLED",0);
        if (encoded == null || encoded.length == 0 || encoded.length > 8 * 1024 * 1024)
            return new Decision(false, "INVALID_IMAGE", 0);
        try { BoundedImage.requireImage(encoded); }
        catch (IOException invalid) { return new Decision(false, "INVALID_IMAGE", 0); }
        MatOfByte bytes = new MatOfByte(encoded);
        Mat image = null;
        try {
            image = Imgcodecs.imdecode(bytes, Imgcodecs.IMREAD_COLOR);
            return evaluateBgr(image, policy);
        } finally { bytes.release(); if (image != null) image.release(); }
    }

    public synchronized Decision evaluateBgr(Mat image, boolean activeRequired) throws Exception {
        return evaluateBgr(image,NativePadPolicy.defaults(activeRequired ? NativePadPolicy.Workflow.OPERATOR : NativePadPolicy.Workflow.RESIDENT));
    }

    public synchronized Decision evaluateBgr(Mat image, NativePadPolicy policy) throws Exception {
        if (policy == null || !policy.enabled) return new Decision(false,"LIVENESS_DISABLED",0);
        if (image == null || image.empty() || image.channels() != 3 || image.cols() < 80 || image.rows() < 80
                || image.cols() > 4096 || image.rows() > 4096)
            return new Decision(false, "INVALID_IMAGE", 0);
        java.util.List<NativeYuNet.Face> found = detector.detect(image);
        if (found.size() != 1) return new Decision(false, found.isEmpty() ? "NO_FACE" : "MULTIPLE_FACES", 0);
        Rect face = found.get(0).box;
        double score = scoreFace(image, face);
        if (!Double.isFinite(score)) return new Decision(false, "MODEL_ERROR", 0);
        if (score <= .45) return new Decision(false, "PRESENTATION_ATTACK", score,face);
        if (score < policy.passiveThreshold || policy.activeRequired) {
            if (!policy.activeEnabled) return new Decision(false,"ACTIVE_DISABLED",score,face);
            return new Decision(false, "ACTIVE_CHALLENGE_REQUIRED", score,face);
        }
        return new Decision(true, "PASSIVE_CLEAR", score,face);
    }

    /** Exact MiniFASNet 2.7x context crop, raw BGR floats, NCHW 1x3x80x80. */
    public synchronized double scoreFace(Mat image, Rect face) throws Exception {
        double scale = Math.min(2.7, Math.min((image.rows() - 1.) / face.height, (image.cols() - 1.) / face.width));
        double width = face.width * scale, height = face.height * scale;
        double left = face.x + face.width / 2. - width / 2., top = face.y + face.height / 2. - height / 2.;
        double right = left + width, bottom = top + height;
        if (left < 0) { right -= left; left = 0; }
        if (top < 0) { bottom -= top; top = 0; }
        if (right > image.cols() - 1) { left -= right - image.cols() + 1; right = image.cols() - 1; }
        if (bottom > image.rows() - 1) { top -= bottom - image.rows() + 1; bottom = image.rows() - 1; }
        Rect box = new Rect((int) left, (int) top, (int) right + 1 - (int) left, (int) bottom + 1 - (int) top);
        Mat crop = image.submat(box), resized = new Mat();
        try {
            Imgproc.resize(crop, resized, new Size(80, 80), 0, 0, Imgproc.INTER_LINEAR);
            byte[] bgr = new byte[80 * 80 * 3]; resized.get(0, 0, bgr);
            float[] tensor = new float[bgr.length];
            for (int i = 0; i < 80 * 80; i++) for (int c = 0; c < 3; c++)
                tensor[c * 80 * 80 + i] = bgr[3 * i + c] & 255;
            return scoreTensor(tensor);
        } finally { crop.release(); resized.release(); }
    }

    public synchronized double scoreTensor(float[] values) throws Exception {
        if (values.length != 3 * 80 * 80) throw new IOException("Invalid PAD tensor dimensions");
        for (float value : values) if (!Float.isFinite(value) || value < 0 || value > 255)
            throw new IOException("Invalid raw BGR tensor value");
        try (OnnxTensor tensor = OnnxTensor.createTensor(environment, FloatBuffer.wrap(values), new long[]{1, 3, 80, 80});
             OrtSession.Result result = session.run(Collections.singletonMap(inputName, tensor))) {
            float[][] output = (float[][]) result.get(0).getValue();
            if (output.length != 1 || output[0].length != 3) throw new IOException("Invalid PAD model output");
            double max = Math.max(output[0][0], Math.max(output[0][1], output[0][2]));
            double sum = 0;
            for (float value : output[0]) {
                if (!Float.isFinite(value)) throw new IOException("Non-finite PAD logits");
                sum += Math.exp(value - max);
            }
            return Math.exp(output[0][1] - max) / sum;
        }
    }

    @Override public void close() throws Exception { try { session.close(); } finally { detector.close(); } }
}
