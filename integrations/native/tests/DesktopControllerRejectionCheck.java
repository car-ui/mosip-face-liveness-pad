import io.mosip.registration.controller.BaseController;
import io.mosip.registration.controller.device.GenericBiometricsController;
import io.mosip.registration.controller.device.Streamer;
import io.mosip.registration.enums.Modality;
import io.mosip.registration.constants.RegistrationConstants;
import io.mosip.registration.context.ApplicationContext;
import io.mosip.registration.dto.packetmanager.BiometricsDto;
import io.mosip.registration.service.bio.BioService;
import io.mosip.registration.service.security.AuthenticationService;
import io.mosip.biometrics.util.ConvertRequestDto;
import io.mosip.biometrics.util.face.FaceEncoder;
import io.mosip.biometrics.util.face.FaceBDIR;
import io.mosip.biometrics.util.face.ImageDataType;
import io.mosip.facepad.DesktopPadCheckpoint;
import io.mosip.facepad.NativeFrameChallenge;
import io.mosip.facepad.NativeActiveSessionCheck;
import java.awt.image.BufferedImage;
import java.io.*;
import java.nio.file.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import javax.imageio.ImageIO;
import javafx.scene.layout.GridPane;

/** Runs the patched upstream controller. The SBI and identity matcher are test doubles. */
public final class DesktopControllerRejectionCheck extends BaseController {
    private static void inject(Object target, String name, Object value) throws Exception {
        Field field = BaseController.class.getDeclaredField(name);
        field.setAccessible(true); field.set(target, value);
    }
    public static void main(String[] args) throws Exception {
        // Exercise the actual upstream Streamer delegation without a UI or camera.
        Streamer stream = new Streamer();
        byte[] markers = {(byte)255, (byte)216, 1, 2, (byte)255, (byte)217};
        ByteArrayOutputStream multipart = new ByteArrayOutputStream();
        for (int i = 0; i < 2; i++) {
            multipart.write("\r\n--camera\r\nContent-Length: 6\r\n\r\n".getBytes(java.nio.charset.StandardCharsets.US_ASCII));
            multipart.write(markers);
        }
        InputStream parts = new ByteArrayInputStream(multipart.toByteArray());
        for (int i = 0; i < 2; i++) {
            if (!Arrays.equals(markers, stream.retrieveNextImage(parts))) throw new AssertionError("Stream frame corrupted");
        }
        java.util.concurrent.ExecutorService reader = java.util.concurrent.Executors.newSingleThreadExecutor(task -> {
            Thread thread = new Thread(task); thread.setDaemon(true); return thread;
        });
        try {
            boolean rejected = reader.submit(() -> {
                try { stream.retrieveNextImage(parts); return false; }
                catch (EOFException expected) { return true; }
            }).get(2, java.util.concurrent.TimeUnit.SECONDS);
            if (!rejected) throw new AssertionError("Camera disconnect accepted");
        } finally { reader.shutdownNow(); }
        final boolean[] closed = {false};
        stream.setUrlStream(new ByteArrayInputStream(new byte[0]) {
            public void close() { closed[0] = true; }
        });
        stream.imageBytes = markers;
        stream.setUrlStream(null);
        if (!closed[0] || stream.getUrlStream() != null || stream.getStreamImageBytes() != null)
            throw new AssertionError("Camera session retained after disconnect");
        System.out.println("PASS actual upstream Streamer: consecutive frames, bounded EOF rejection and disconnect cleanup");
        ApplicationContext.getInstance();
        Map<String,Object> policy = new HashMap<>();
        policy.put(RegistrationConstants.SERVER_ACTIVE_PROFILE, "Developer");
        policy.put(RegistrationConstants.CAPTURE_TIME_OUT, "10");
        policy.put(RegistrationConstants.FACE_THRESHOLD, "60");
        ApplicationContext.setApplicationMap(policy);
        ByteArrayOutputStream jpeg = new ByteArrayOutputStream();
        ImageIO.write(new BufferedImage(640,480,BufferedImage.TYPE_3BYTE_BGR), "jpg", jpeg);
        ConvertRequestDto convert = new ConvertRequestDto();
        convert.setVersion("ISO19794_5_2011"); convert.setPurpose("REGISTRATION");
        convert.setInputBytes(jpeg.toByteArray()); convert.setImageType(0);
        BiometricsDto biometric = new BiometricsDto();
        biometric.setAttributeISO(FaceEncoder.convertFaceImageToISO(convert));
        if (args.length == 2) Files.write(Paths.get(args[1]), biometric.getAttributeISO());
        biometric.setBioAttribute("face"); biometric.setQualityScore(99.0);
        List<BiometricsDto> candidates = new ArrayList<>(); candidates.add(biometric);
        // Registration checkpoint must reject the same ISO candidate before storage.
        try { DesktopPadCheckpoint.requireClear(candidates, false); throw new AssertionError("Blank registration accepted"); }
        catch (IOException expected) {
            if (!expected.getMessage().contains("NO_FACE")) throw expected;
            System.out.println("PASS registration checkpoint rejects decoded blank ISO: NO_FACE");
        }
        GenericBiometricsController resident = new GenericBiometricsController();
        Field pane = GenericBiometricsController.class.getDeclaredField("checkBoxPane");
        pane.setAccessible(true); pane.set(resident, new GridPane());
        Field residentDevice = GenericBiometricsController.class.getDeclaredField("bioService");
        residentDevice.setAccessible(true);
        residentDevice.set(resident, Proxy.newProxyInstance(BioService.class.getClassLoader(), new Class[]{BioService.class},
                (proxy, method, values) -> method.getName().equals("getMDMQualityThreshold") ? 60.0 : candidates));
        Method residentCapture = GenericBiometricsController.class.getDeclaredMethod("rCapture", String.class, Modality.class);
        residentCapture.setAccessible(true);
        try { residentCapture.invoke(resident, "syntheticResident", Modality.FACE); throw new AssertionError("Resident capture returned rejected candidate"); }
        catch (InvocationTargetException e) {
            if (!(e.getCause() instanceof IOException) || !e.getCause().getMessage().contains("NO_FACE")) throw e;
            System.out.println("PASS upstream GenericBiometricsController rejects blank ISO before returning candidates for storage");
        }
        AtomicInteger captures = new AtomicInteger(), matches = new AtomicInteger();
        BioService device = (BioService) Proxy.newProxyInstance(BioService.class.getClassLoader(), new Class[]{BioService.class},
                (proxy, method, values) -> { captures.incrementAndGet(); return candidates; });
        AuthenticationService matcher = (AuthenticationService) Proxy.newProxyInstance(AuthenticationService.class.getClassLoader(), new Class[]{AuthenticationService.class},
                (proxy, method, values) -> { matches.incrementAndGet(); return true; });
        DesktopControllerRejectionCheck controller = new DesktopControllerRejectionCheck();
        inject(controller, "bioService", device); inject(controller, "authenticationService", matcher);
        for (boolean reviewer : new boolean[]{false,true}) {
            try { controller.captureAndValidateFace("SYNTHETIC-TEST-ONLY", true, reviewer); throw new AssertionError("Rejected face reached authentication"); }
            catch (IOException expected) {
                if (!expected.getMessage().contains("NO_FACE")) throw expected;
            }
        }
        if (captures.get() != 2 || matches.get() != 0) throw new AssertionError("Matcher called despite rejection");
        System.out.println("PASS upstream BaseController operator/supervisor rejection: captures=2, identityMatcherCalls=0");
        if (args.length >= 1) {
            // Attributed static NASA fixture, not a physical attack or a camera capture.
            ByteArrayOutputStream portraitJpeg = new ByteArrayOutputStream();
            if (!ImageIO.write(ImageIO.read(Paths.get(args[0]).toFile()), "jpg", portraitJpeg))
                throw new IOException("Cannot encode portrait fixture as JPEG");
            convert.setInputBytes(portraitJpeg.toByteArray());
            biometric.setAttributeISO(FaceEncoder.convertFaceImageToISO(convert));
            // This pinned FaceEncoder convenience method always marks bytes as
            // lossless JPEG2000, even when input is JPEG. Correct the test record's
            // declared format to match its bytes before checking exact binding.
            FaceBDIR record = new FaceBDIR(new DataInputStream(new ByteArrayInputStream(biometric.getAttributeISO())));
            record.getRepresentation().getRepresentationHeader().getImageInformation().setImageDataType(ImageDataType.JPEG);
            ByteArrayOutputStream corrected = new ByteArrayOutputStream();
            record.writeObject(new DataOutputStream(corrected));
            biometric.setAttributeISO(corrected.toByteArray());
            boolean passiveClear = false;
            try { DesktopPadCheckpoint.requireClear(candidates, false); passiveClear = true; }
            catch (IOException expected) {
                if (!expected.getMessage().contains("ACTIVE_CHALLENGE_REQUIRED")) throw expected;
            }
            for (boolean reviewer : new boolean[]{false,true}) {
                try { controller.captureAndValidateFace("SYNTHETIC-TEST-ONLY", true, reviewer); throw new AssertionError("Active evidence bypassed"); }
                catch (IOException expected) {
                    if (!expected.getMessage().contains("ACTIVE_CHALLENGE_REQUIRED")) throw expected;
                }
            }
            if (captures.get() != 4 || matches.get() != 0) throw new AssertionError("Matcher called without active evidence");
            System.out.println("PASS recorded NASA portrait rejected for operator/supervisor: ACTIVE_CHALLENGE_REQUIRED; identityMatcherCalls=0; passiveClear=" + passiveClear);
            // Inject only session geometry for this controller-path test. Production
            // sessions receive actual PAD/landmark observations from the native stream.
            Field evidence = NativeFrameChallenge.class.getDeclaredField("session");
            evidence.setAccessible(true);
            for (boolean reviewer : new boolean[]{false,true}) {
                NativeFrameChallenge proof = DesktopPadCheckpoint.newFrameChallenge();
                evidence.set(proof, NativeActiveSessionCheck.completedForControllerTest(portraitJpeg.toByteArray()));
                if (!controller.captureAndValidateFace("SYNTHETIC-TEST-ONLY", false, reviewer, proof))
                    throw new AssertionError("Exact active frame did not reach matcher double");
            }
            if (matches.get() != 2) throw new AssertionError("Expected two calls to matcher double");
            NativeFrameChallenge mismatch = DesktopPadCheckpoint.newFrameChallenge();
            evidence.set(mismatch, NativeActiveSessionCheck.completedForControllerTest(new byte[]{(byte)255,(byte)216,0,0,(byte)255,(byte)217}));
            try {
                controller.captureAndValidateFace("SYNTHETIC-TEST-ONLY", false, false, mismatch);
                throw new AssertionError("Different final image reached matcher");
            } catch (IOException expected) {
                if (!expected.getMessage().contains("ACTIVE_CHALLENGE_REQUIRED")) throw expected;
            }
            if (matches.get() != 2) throw new AssertionError("Mismatched proof reached matcher");
            System.out.println("PASS actual BaseController exact-frame binding: injected completed geometry reaches matcher double for both roles; different final JPEG rejects before matcher");
        }
        System.out.println("Evidence scope: synthetic ISO + actual upstream controller/model, no live UI or physical attack.");
    }
}
