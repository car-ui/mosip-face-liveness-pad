package io.mosip.facepad;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import java.io.IOException;
import java.nio.FloatBuffer;
import java.util.Collections;
import org.opencv.core.*;
import org.opencv.imgproc.Imgproc;

/** Research geometric action input. It does not identify a person or approve a capture. */
public final class NativeLandmarkEngine implements AutoCloseable {
    public static final String MODEL_SHA256 = "09c96e67163c660431d37eccc24d40172e514fe4f5768ebf507941e3cb9e3bfb";
    private final OrtEnvironment environment = OrtEnvironment.getEnvironment();
    private final OrtSession session;
    private final String inputName;

    public static final class Observation {
        public final float[] landmarks;
        public final double presence, leftEar, rightEar, turnRatio;
        Observation(float[] values, double presence) throws IOException {
            this.landmarks = values;
            this.presence = presence;
            leftEar = ear(values, new int[]{33,160,158,133,153,144});
            rightEar = ear(values, new int[]{362,385,387,263,373,380});
            double left = Math.abs(values[3] - values[33 * 3]);
            double right = Math.abs(values[263 * 3] - values[3]);
            if (left + right < 1) throw new IOException("Degenerate face geometry");
            turnRatio = (left - right) / (left + right);
        }
    }

    public NativeLandmarkEngine(byte[] model) throws Exception {
        if (!MODEL_SHA256.equals(NativePadEngine.sha256(model))) throw new IOException("Landmark model checksum mismatch");
        try (OrtSession.SessionOptions options = new OrtSession.SessionOptions()) {
            options.setIntraOpNumThreads(Math.max(1, Math.min(2, Runtime.getRuntime().availableProcessors())));
            options.setInterOpNumThreads(1);
            session = environment.createSession(model, options);
        }
        inputName = session.getInputNames().iterator().next();
    }

    /** Explicit face ROI: square 1.5x context, RGB float [0,1], NHWC 1x256x256x3. */
    public synchronized Observation observe(Mat bgr, Rect face) throws Exception {
        if (bgr == null || bgr.empty() || bgr.type() != CvType.CV_8UC3 || face == null
                || face.width < 40 || face.height < 40 || face.x < 0 || face.y < 0
                || face.x + face.width > bgr.cols() || face.y + face.height > bgr.rows())
            throw new IOException("Invalid landmark image or face ROI");
        int side = (int) Math.round(Math.max(face.width, face.height) * 1.5);
        int x = face.x + face.width / 2 - side / 2;
        int y = face.y + face.height / 2 - side / 2;
        // Reject rather than distort an ROI that falls outside the image.
        if (x < 0 || y < 0 || x + side > bgr.cols() || y + side > bgr.rows())
            throw new IOException("Face too close to image edge");
        Mat crop = bgr.submat(new Rect(x, y, side, side)), resized = new Mat(), rgb = new Mat();
        try {
            Imgproc.resize(crop, resized, new Size(256,256), 0, 0, Imgproc.INTER_LINEAR);
            Imgproc.cvtColor(resized, rgb, Imgproc.COLOR_BGR2RGB);
            byte[] bytes = new byte[256 * 256 * 3]; rgb.get(0, 0, bytes);
            float[] tensor = new float[bytes.length];
            for (int i = 0; i < bytes.length; i++) tensor[i] = (bytes[i] & 255) / 255f;
            return infer(tensor);
        } finally { crop.release(); resized.release(); rgb.release(); }
    }

    public synchronized Observation infer(float[] values) throws Exception {
        if (values == null || values.length != 256 * 256 * 3) throw new IOException("Invalid landmark tensor dimensions");
        for (float v : values) if (!Float.isFinite(v) || v < 0 || v > 1)
            throw new IOException("Invalid RGB landmark tensor value");
        try (OnnxTensor tensor = OnnxTensor.createTensor(environment, FloatBuffer.wrap(values), new long[]{1,256,256,3});
             OrtSession.Result outputs = session.run(Collections.singletonMap(inputName, tensor))) {
            float[] points = ((float[][][][]) outputs.get("Identity").get().getValue())[0][0][0];
            float logit = ((float[][][][]) outputs.get("Identity_1").get().getValue())[0][0][0][0];
            if (points.length != 478 * 3 || !Float.isFinite(logit)) throw new IOException("Invalid landmark output");
            for (float value : points) if (!Float.isFinite(value)) throw new IOException("Non-finite landmark output");
            double presence = 1.0 / (1.0 + Math.exp(-logit));
            if (presence < .9) throw new IOException("Landmark face presence too low");
            return new Observation(points.clone(), presence);
        }
    }

    private static double distance(float[] points, int a, int b) {
        return Math.hypot(points[a * 3] - points[b * 3], points[a * 3 + 1] - points[b * 3 + 1]);
    }
    private static double ear(float[] points, int[] indices) throws IOException {
        double width = distance(points, indices[0], indices[3]);
        if (width < 1) throw new IOException("Degenerate eye geometry");
        return (distance(points, indices[1], indices[5]) + distance(points, indices[2], indices[4])) / (2 * width);
    }
    @Override public void close() throws Exception { session.close(); }
}
