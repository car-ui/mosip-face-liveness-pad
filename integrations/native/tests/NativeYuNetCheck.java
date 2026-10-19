import io.mosip.facepad.NativeYuNet;
import java.nio.file.*;
import java.util.*;
import org.opencv.core.Mat;
import org.opencv.imgcodecs.Imgcodecs;

/** Real model/decoder parity against explicit OpenCV reference detections. */
public final class NativeYuNetCheck {
    public static void main(String[] args) throws Exception {
        ai.onnxruntime.OrtEnvironment.getEnvironment();
        nu.pattern.OpenCV.loadLocally();
        byte[] model = Files.readAllBytes(Paths.get(args[0]));
        int cases = 0;
        try (NativeYuNet detector = new NativeYuNet(model)) {
            for (String row : Files.readAllLines(Paths.get(args[1]))) {
                String[] columns = row.split("\\t",-1);
                Mat image = Imgcodecs.imread(columns[0]);
                try {
                    List<NativeYuNet.Face> actual = detector.detect(image);
                    int count = Integer.parseInt(columns[1]);
                    if (actual.size() != count) throw new AssertionError("Face count mismatch in " + columns[0]);
                    double tolerance = Math.max(2,Math.ceil(Math.max(image.cols(),image.rows()) / 640.) + 1);
                    for (int i=0;i<count;i++) {
                        String[] expected = columns[i+2].split(",");
                        NativeYuNet.Face face = actual.get(i);
                        int[] values = {face.box.x,face.box.y,face.box.width,face.box.height};
                        for (int j=0;j<4;j++) if (Math.abs(values[j]-Double.parseDouble(expected[j])) > tolerance)
                            throw new AssertionError("Face geometry mismatch in " + columns[0]);
                        if (Math.abs(face.score-Double.parseDouble(expected[4])) > .0005)
                            throw new AssertionError("Face confidence mismatch");
                    }
                    cases++;
                } finally { image.release(); }
            }
            boolean invalid = false;
            try { detector.detect(new Mat()); } catch (Exception expected) { invalid = true; }
            if (!invalid) throw new AssertionError("Invalid input accepted");
        }
        model[0] ^= 1;
        boolean blocked = false;
        try (NativeYuNet ignored = new NativeYuNet(model)) { }
        catch (Exception expected) { blocked = true; }
        if (!blocked) throw new AssertionError("Tampered face model loaded");
        System.out.println("PASS " + cases + " real YuNet fixture parity cases; invalid input and tampered model rejected");
    }
}
