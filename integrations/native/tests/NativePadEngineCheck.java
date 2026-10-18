import io.mosip.facepad.NativePadEngine;
import java.nio.file.*;
import java.nio.*;
import org.opencv.core.*;

/** Executes the packaged ONNX graph, rather than substituting model scores. */
public final class NativePadEngineCheck {
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        nu.pattern.OpenCV.loadLocally();
        Path root = Paths.get(args[0]);
        byte[] model = Files.readAllBytes(root.resolve("assets/models/minifasnet_v2.onnx"));
        Path cascade = root.resolve("integrations/native/assets/haarcascade_frontalface_default.xml");
        try (NativePadEngine engine = new NativePadEngine(model, cascade)) {
            byte[] input = Files.readAllBytes(Paths.get(args[1]));
            FloatBuffer buffer = ByteBuffer.wrap(input).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer();
            float[] tensor = new float[buffer.remaining()]; buffer.get(tensor);
            double actual = engine.scoreTensor(tensor), expected = Double.parseDouble(args[2]);
            require(Math.abs(actual - expected) < 1e-5, "Java/Python inference mismatch: " + actual + " vs " + expected);
            Mat blank = Mat.zeros(480, 640, CvType.CV_8UC3);
            try {
                require(!engine.evaluateBgr(blank, false).accepted, "Blank image accepted");
                require("NO_FACE".equals(engine.evaluateBgr(blank, true).reason), "Unexpected blank reason");
            } finally { blank.release(); }
            require(!engine.evaluateEncoded(new byte[]{1,2,3}, false).accepted, "Malformed image accepted");
            boolean invalidTensor = false;
            tensor[0] = Float.NaN;
            try { engine.scoreTensor(tensor); } catch (Exception e) { invalidTensor = true; }
            require(invalidTensor, "Non-finite tensor accepted");
            System.out.println("PASS actual ONNX Java/Python parity; blank and malformed rejection; invalid tensor rejection. liveScore=" + actual);
        }
        model[model.length - 1] ^= 1;
        boolean tampered = false;
        try (NativePadEngine ignored = new NativePadEngine(model, cascade)) { }
        catch (Exception e) { tampered = true; }
        require(tampered, "Tampered model loaded");
        System.out.println("PASS model tampering rejection");
    }
}
