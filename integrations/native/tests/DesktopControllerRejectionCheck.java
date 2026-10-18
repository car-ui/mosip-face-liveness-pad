import io.mosip.registration.controller.BaseController;
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
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import javax.imageio.ImageIO;

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
        biometric.setBioAttribute("face"); biometric.setQualityScore(99.0);
        List<BiometricsDto> candidates = Collections.singletonList(biometric);
        // Registration checkpoint must reject the same ISO candidate before storage.
        try { DesktopPadCheckpoint.requireClear(candidates, false); throw new AssertionError("Blank registration accepted"); }
        catch (IOException expected) {
            if (!expected.getMessage().contains("NO_FACE")) throw expected;
            System.out.println("PASS registration checkpoint rejects decoded blank ISO: NO_FACE");
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
        System.out.println("Evidence scope: synthetic ISO + actual upstream controller/model, no live UI or physical attack.");
    }
}
