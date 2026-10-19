import io.mosip.facepad.NativeLandmarkEngine;
import io.mosip.facepad.NativePadEngine;
import io.mosip.facepad.NativeFrameChallenge;
import io.mosip.facepad.NativeActiveSession;
import java.nio.*;
import java.nio.file.*;
import java.io.IOException;
import org.opencv.core.*;
import org.opencv.imgcodecs.Imgcodecs;

/** Real Java ONNX inference against Python, plus geometry and fail-closed inputs. */
public final class NativeLandmarkEngineCheck {
    public static void main(String[] args) throws Exception {
        nu.pattern.OpenCV.loadLocally();
        Path root = Paths.get(args[0]);
        byte[] model = Files.readAllBytes(root.resolve("assets/models/facemesh_v2.onnx"));
        Mat image = Imgcodecs.imread(root.resolve("tests/sample_images/astronaut.png").toString());
        try (NativeLandmarkEngine engine = new NativeLandmarkEngine(model)) {
            float[] input = floats(Paths.get(args[1])), expected = floats(Paths.get(args[2]));
            NativeLandmarkEngine.Observation result = engine.infer(input);
            if (expected.length != result.landmarks.length) throw new AssertionError("Wrong landmark count");
            double error = 0;
            for (int i = 0; i < expected.length; i++) error = Math.max(error, Math.abs(expected[i] - result.landmarks[i]));
            if (error > .002) throw new AssertionError("Java/Python landmark mismatch " + error);
            if (result.presence < .9 || !Double.isFinite(result.leftEar) || !Double.isFinite(result.rightEar))
                throw new AssertionError("Invalid geometry");
            NativeLandmarkEngine.Observation photo = engine.observe(image, new Rect(172,64,102,102));
            System.out.println("PASS actual Java/Python landmark inference; maxAbsError=" + error + "; presence=" + result.presence);
            System.out.println("PASS recorded-photo crop geometry; leftEAR=" + photo.leftEar + "; rightEAR=" + photo.rightEar + "; turnRatio=" + photo.turnRatio);
            boolean missing = false;
            try { engine.infer(new float[256 * 256 * 3]); } catch (IOException expectedError) { missing = true; }
            if (!missing) throw new AssertionError("Blank input supplied face evidence");
            for (float invalid : new float[]{Float.NaN, Float.POSITIVE_INFINITY, -.1f, 1.1f}) {
                input[0] = invalid;
                try { engine.infer(input); throw new AssertionError("Invalid tensor accepted"); }
                catch (IOException expectedError) { }
            }
            try { engine.observe(image, new Rect(0,0,100,100)); throw new AssertionError("Edge crop distorted"); }
            catch (IOException expectedError) { }
            System.out.println("PASS blank presence, invalid values and clipped crop rejected");
            Path cascade = root.resolve("integrations/native/assets/haarcascade_frontalface_default.xml");
            try (NativePadEngine pad = new NativePadEngine(Files.readAllBytes(root.resolve("assets/models/minifasnet_v2.onnx")), Files.readAllBytes(root.resolve("assets/models/face_detection_yunet_2023mar.onnx")))) {
                NativeFrameChallenge active = new NativeFrameChallenge(pad, engine, cascade, 10000);
                MatOfByte jpeg = new MatOfByte();
                try {
                    Imgcodecs.imencode(".jpg", image, jpeg);
                    byte[] bytes = jpeg.toArray();
                    for (int i = 0; i < 12; i++) active.observe(bytes);
                    if (active.state() == NativeActiveSession.State.COMPLETE || active.consume(bytes))
                        throw new AssertionError("Repeated static photograph completed active challenge");
                    System.out.println("PASS actual PAD/landmark frame bridge does not complete actions on repeated recorded photo; state=" + active.state());
                } finally { jpeg.release(); }
            }
        } finally { image.release(); }
        model[model.length - 1] ^= 1;
        try (NativeLandmarkEngine ignored = new NativeLandmarkEngine(model)) { throw new AssertionError("Tampered model loaded"); }
        catch (IOException expected) { }
        System.out.println("PASS landmark model tampering rejected; no active completion or physical accuracy claim");
    }

    private static float[] floats(Path path) throws Exception {
        FloatBuffer buffer = ByteBuffer.wrap(Files.readAllBytes(path)).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer();
        float[] values = new float[buffer.remaining()]; buffer.get(values); return values;
    }
}
