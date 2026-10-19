package io.mosip.facepad;

import ai.onnxruntime.*;
import java.io.IOException;
import java.nio.FloatBuffer;
import java.security.MessageDigest;
import java.util.*;
import org.opencv.core.*;
import org.opencv.imgproc.Imgproc;

/** Fixed-input YuNet adapter, with decoding checked against OpenCV's reference. */
public final class NativeYuNet implements AutoCloseable {
    public static final String MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4";
    private final OrtEnvironment environment = OrtEnvironment.getEnvironment();
    private final OrtSession session;
    private static final int SIZE = 640;

    public static final class Face {
        public final Rect box;
        public final double score;
        private Face(Rect box, double score) { this.box = box; this.score = score; }
    }

    public NativeYuNet(byte[] model) throws Exception {
        if (model == null || !MODEL_SHA256.equals(hex(MessageDigest.getInstance("SHA-256").digest(model))))
            throw new IOException("Face model checksum mismatch");
        try (OrtSession.SessionOptions options = new OrtSession.SessionOptions()) {
            options.setIntraOpNumThreads(Math.max(1, Math.min(2, Runtime.getRuntime().availableProcessors())));
            options.setInterOpNumThreads(1);
            session = environment.createSession(model, options);
        }
    }

    public synchronized List<Face> detect(Mat image) throws Exception {
        if (image == null || image.empty() || image.type() != CvType.CV_8UC3 || image.cols() > 4096
                || image.rows() > 4096 || image.cols() < 16 || image.rows() < 16)
            throw new IOException("Invalid face detector input");
        double scale = Math.min(SIZE / (double) image.cols(), SIZE / (double) image.rows());
        int width = Math.max(1, (int) Math.round(image.cols() * scale));
        int height = Math.max(1, (int) Math.round(image.rows() * scale));
        Mat resized = new Mat(), canvas = Mat.zeros(SIZE, SIZE, CvType.CV_8UC3);
        Mat region = canvas.submat(new Rect(0, 0, width, height));
        try {
            Imgproc.resize(image, resized, new Size(width, height), 0, 0, Imgproc.INTER_LINEAR);
            resized.copyTo(region);
            byte[] pixels = new byte[SIZE * SIZE * 3];
            canvas.get(0, 0, pixels);
            float[] values = new float[pixels.length];
            for (int i = 0; i < SIZE * SIZE; i++) for (int c = 0; c < 3; c++)
                values[c * SIZE * SIZE + i] = pixels[3 * i + c] & 255;
            List<Face> candidates = new ArrayList<>();
            try (OnnxTensor input = OnnxTensor.createTensor(environment, FloatBuffer.wrap(values),
                         new long[]{1, 3, SIZE, SIZE});
                 OrtSession.Result result = session.run(Collections.singletonMap("input", input))) {
                for (int stride : new int[]{8, 16, 32}) {
                    float[][] cls = tensor(result, "cls_" + stride);
                    float[][] obj = tensor(result, "obj_" + stride);
                    float[][] boxes = tensor(result, "bbox_" + stride);
                    int columns = SIZE / stride;
                    if (cls.length != columns * columns || obj.length != cls.length || boxes.length != cls.length)
                        throw new IOException("Unexpected face output shape");
                    for (int i = 0; i < cls.length; i++) {
                        if (!Float.isFinite(cls[i][0]) || !Float.isFinite(obj[i][0]))
                            throw new IOException("Invalid face confidence");
                        double score = Math.sqrt(clamp(cls[i][0]) * clamp(obj[i][0]));
                        if (score < .9) continue;
                        if (boxes[i].length != 4) throw new IOException("Invalid face box output");
                        double cx = (i % columns + boxes[i][0]) * stride;
                        double cy = (i / columns + boxes[i][1]) * stride;
                        double w = Math.exp(boxes[i][2]) * stride, h = Math.exp(boxes[i][3]) * stride;
                        if (!Double.isFinite(cx + cy + w + h)) throw new IOException("Invalid face geometry");
                        // NMS uses integer boxes in model coordinates, matching the reference.
                        candidates.add(new Face(new Rect((int)(cx - w / 2), (int)(cy - h / 2),
                                Math.max(1, (int)w), Math.max(1, (int)h)), score));
                    }
                }
            }
            candidates.sort((a,b) -> Double.compare(b.score,a.score));
            List<Face> selected = new ArrayList<>();
            for (int i = 0; i < Math.min(5000, candidates.size()); i++) {
                Face candidate = candidates.get(i);
                boolean duplicate = false;
                for (Face face : selected) if (iou(candidate.box,face.box) > .3) { duplicate = true; break; }
                if (!duplicate) selected.add(candidate);
            }
            List<Face> mapped = new ArrayList<>();
            double sx = width / (double)image.cols(), sy = height / (double)image.rows();
            for (Face face : selected) {
                int left = Math.max(0,(int)(face.box.x / sx));
                int top = Math.max(0,(int)(face.box.y / sy));
                int right = Math.min(image.cols(),(int)((face.box.x + face.box.width) / sx));
                int bottom = Math.min(image.rows(),(int)((face.box.y + face.box.height) / sy));
                if (right > left && bottom > top) mapped.add(new Face(new Rect(left,top,right-left,bottom-top),face.score));
            }
            return mapped;
        } finally { region.release(); resized.release(); canvas.release(); }
    }

    private static float[][] tensor(OrtSession.Result result,String name) throws Exception {
        Object value = result.get(name).orElseThrow(() -> new IOException("Missing face output")).getValue();
        if (!(value instanceof float[][][]) || ((float[][][])value).length != 1)
            throw new IOException("Invalid face output rank");
        return ((float[][][])value)[0];
    }
    private static double clamp(float value) { return Math.max(0,Math.min(1,value)); }
    private static double iou(Rect a,Rect b) {
        double overlap = Math.max(0,Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)) *
                         (double)Math.max(0,Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y));
        return overlap / Math.max(1,a.width*(double)a.height+b.width*(double)b.height-overlap);
    }
    private static String hex(byte[] bytes) {
        StringBuilder result = new StringBuilder();
        for (byte value : bytes) result.append(String.format("%02x",value & 255));
        return result.toString();
    }
    @Override public void close() throws Exception { session.close(); }
}
