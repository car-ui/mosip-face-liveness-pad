import io.mosip.registration.controller.BaseController;
import io.mosip.registration.controller.device.GenericBiometricsController;
import io.mosip.registration.enums.Modality;
import io.mosip.registration.constants.RegistrationConstants;
import io.mosip.registration.context.ApplicationContext;
import io.mosip.registration.dto.packetmanager.BiometricsDto;
import io.mosip.registration.service.bio.BioService;
import io.mosip.registration.service.security.AuthenticationService;
import io.mosip.biometrics.util.ConvertRequestDto;
import io.mosip.biometrics.util.face.FaceEncoder;
import io.mosip.facepad.DesktopPadCheckpoint;
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
            // Existing repository portrait fixture, not a physical attack or a camera capture.
            convert.setInputBytes(Files.readAllBytes(Paths.get(args[0])));
            biometric.setAttributeISO(FaceEncoder.convertFaceImageToISO(convert));
            DesktopPadCheckpoint.requireClear(candidates, false);
            for (boolean reviewer : new boolean[]{false,true}) {
                try { controller.captureAndValidateFace("SYNTHETIC-TEST-ONLY", true, reviewer); throw new AssertionError("Active evidence bypassed"); }
                catch (IOException expected) {
                    if (!expected.getMessage().contains("ACTIVE_CHALLENGE_REQUIRED")) throw expected;
                }
            }
            if (captures.get() != 4 || matches.get() != 0) throw new AssertionError("Matcher called without active evidence");
            System.out.println("PASS high-passive-score portrait still rejected for operator/supervisor: ACTIVE_CHALLENGE_REQUIRED; identityMatcherCalls=0");
        }
        System.out.println("Evidence scope: synthetic ISO + actual upstream controller/model, no live UI or physical attack.");
    }
}
