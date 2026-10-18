package io.mosip.registration_client.api_services;

import static org.junit.Assert.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import android.app.Activity;
import android.content.Context;
import android.net.Uri;
import android.os.Bundle;
import android.os.Build;
import android.os.Debug;
import android.os.SystemClock;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.mosip.facepad.AndroidPadCheckpoint;
import io.mosip.facepad.NativePadEngine;
import io.mosip.registration.clientmanager.constant.Modality;
import io.mosip.registration.clientmanager.constant.RegistrationConstants;
import io.mosip.registration.clientmanager.dto.registration.BiometricsDto;
import io.mosip.registration.clientmanager.dto.registration.RegistrationDto;
import io.mosip.registration.clientmanager.repository.GlobalParamRepository;
import io.mosip.registration.clientmanager.service.Biometrics095Service;
import io.mosip.registration.clientmanager.service.UserOnboardService;
import io.mosip.registration.clientmanager.spi.AuditManagerService;
import io.mosip.registration.clientmanager.spi.RegistrationService;
import io.mosip.registration_client.model.BiometricsPigeon;
import java.io.*;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.json.JSONObject;

/** Actual Android JNI/model and acceptance API; SBI parser is an explicit test double. */
@RunWith(AndroidJUnit4.class)
public class NativePadAcceptanceTest {
    private static void set(Object target, String fieldName, Object value) throws Exception {
        Field field = BiometricsDetailsApi.class.getDeclaredField(fieldName);
        field.setAccessible(true); field.set(target, value);
    }

    private BiometricsDto blankFace() throws Exception {
        try (InputStream input = InstrumentationRegistry.getInstrumentation().getContext().getAssets().open("blank-face.iso");
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192]; int count;
            while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
            BiometricsDto result = new BiometricsDto();
            result.setBioValue(Base64.getUrlEncoder().withoutPadding().encodeToString(output.toByteArray()));
            result.setModality("Face"); result.setQualityScore(99);
            return result;
        }
    }

    @Test public void actualPackagedModelRejectsBlankIso() throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        try {
            AndroidPadCheckpoint.requireClear(context, Collections.singletonList(blankFace()), false);
            fail("Blank ISO face accepted");
        } catch (IOException expected) { assertTrue(expected.getMessage(), expected.getMessage().contains("NO_FACE")); }
    }

    @Test public void actualAndroidOnnxForwardPassMatchesPython() throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        Method factory = AndroidPadCheckpoint.class.getDeclaredMethod("engine", Context.class);
        factory.setAccessible(true);
        NativePadEngine engine = (NativePadEngine) factory.invoke(null, context);
        float[] input = new float[3 * 80 * 80];
        for (int i = 0; i < input.length; i++) input[i] = i % 256;
        // Reference from Python ORT and the exact packaged model hash. Synthetic tensor only.
        assertEquals(8.380277904507238e-6, engine.scoreTensor(input), 1e-7);
    }

    @Test public void actualAndroidInferenceTimingAndMemory() throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        Method factory = AndroidPadCheckpoint.class.getDeclaredMethod("engine", Context.class);
        factory.setAccessible(true);
        NativePadEngine engine = (NativePadEngine) factory.invoke(null, context);
        float[] input = new float[3 * 80 * 80];
        for (int i = 0; i < input.length; i++) input[i] = i % 256;
        for (int i = 0; i < 10; i++) engine.scoreTensor(input);
        double[] milliseconds = new double[100];
        for (int i = 0; i < milliseconds.length; i++) {
            long start = SystemClock.elapsedRealtimeNanos();
            double score = engine.scoreTensor(input);
            milliseconds[i] = (SystemClock.elapsedRealtimeNanos() - start) / 1_000_000.0;
            assertEquals(8.380277904507238e-6, score, 1e-7);
        }
        Arrays.sort(milliseconds);
        Debug.MemoryInfo memory = new Debug.MemoryInfo();
        Debug.getMemoryInfo(memory);
        Runtime runtime = Runtime.getRuntime();
        JSONObject metrics = new JSONObject();
        metrics.put("scope", "ONNX scoreTensor only; synthetic input; no camera, face detection or full capture");
        metrics.put("modelSha256", NativePadEngine.MODEL_SHA256);
        metrics.put("api", Build.VERSION.SDK_INT);
        metrics.put("abis", Arrays.toString(Build.SUPPORTED_ABIS));
        metrics.put("deviceModel", Build.MODEL);
        metrics.put("availableProcessors", runtime.availableProcessors());
        metrics.put("intraOpThreads", engine.getInferenceThreads());
        metrics.put("warmups", 10);
        metrics.put("iterations", milliseconds.length);
        metrics.put("p50Ms", milliseconds[49]);
        metrics.put("p95Ms", milliseconds[94]);
        metrics.put("minMs", milliseconds[0]);
        metrics.put("maxMs", milliseconds[milliseconds.length - 1]);
        metrics.put("processTotalPssKb", memory.getTotalPss());
        metrics.put("processJavaHeapUsedBytes", runtime.totalMemory() - runtime.freeMemory());
        metrics.put("memoryScope", "Whole instrumentation target process after benchmark, not incremental model memory");
        Bundle results = new Bundle();
        results.putString("facepadBenchmarkJson", metrics.toString());
        // Keep the measured values in the final instrumentation result, not only logcat.
        InstrumentationRegistry.getInstrumentation().addResults(results);
    }

    @Test public void residentApiRejectsBeforeStorage() throws Exception { exerciseApi(false); }
    @Test public void onboardingApiRejectsBeforeStorage() throws Exception { exerciseApi(true); }

    private void exerciseApi(boolean operator) throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        AuditManagerService audit = mock(AuditManagerService.class);
        Biometrics095Service sbi = mock(Biometrics095Service.class);
        RegistrationService registrations = mock(RegistrationService.class);
        RegistrationDto registration = mock(RegistrationDto.class);
        UserOnboardService onboarding = mock(UserOnboardService.class);
        List<BiometricsDto> operatorStorage = new ArrayList<>();
        when(registrations.getRegistrationDto()).thenReturn(registration);
        when(registration.getCaptureTransactionId()).thenReturn("SYNTHETIC-NATIVE-TEST");
        when(onboarding.getCaptureTransactionId()).thenReturn("SYNTHETIC-NATIVE-TEST");
        when(onboarding.getOperatorBiometrics()).thenReturn(operatorStorage);
        when(sbi.handleRCaptureResponse(eq(Modality.FACE), any(InputStream.class), anyList(),
                eq("SYNTHETIC-NATIVE-TEST"), eq(operator))).thenReturn(Collections.singletonList(blankFace()));
        Activity activity = mock(Activity.class);
        when(activity.getApplicationContext()).thenReturn(context);
        when(activity.getContentResolver()).thenReturn(context.getContentResolver());
        when(activity.getAssets()).thenReturn(context.getAssets());
        when(activity.getCacheDir()).thenReturn(context.getCacheDir());
        BiometricsDetailsApi api = new BiometricsDetailsApi(audit, new ObjectMapper(), sbi, registrations,
                mock(GlobalParamRepository.class), onboarding);
        set(api, "activity", activity); set(api, "currentModality", Modality.FACE);
        set(api, "fieldId", operator ? "operatorBiometrics" : "syntheticResident");
        AtomicReference<Throwable> rejection = new AtomicReference<>();
        AtomicReference<String> success = new AtomicReference<>();
        api.biometricResult = new BiometricsPigeon.Result<String>() {
            @Override public void success(String value) { success.set(value); }
            @Override public void error(Throwable error) { rejection.set(error); }
        };
        File response = File.createTempFile("native-pad-test-", ".json", context.getCacheDir());
        try {
            Bundle bundle = new Bundle(); bundle.putParcelable(RegistrationConstants.SBI_INTENT_RESPONSE_KEY, Uri.fromFile(response));
            InstrumentationRegistry.getInstrumentation().runOnMainSync(() -> api.parseRCaptureResponse(bundle));
            assertNull("Capture was reported as accepted", success.get());
            assertNotNull("Rejection callback missing", rejection.get());
            assertTrue(rejection.get().getMessage(), rejection.get().getMessage().contains("NO_FACE"));
            verify(registration, never()).addBiometric(anyString(), anyString(), anyInt(), any(BiometricsDto.class));
            assertTrue("Operator storage changed despite rejection", operatorStorage.isEmpty());
        } finally { response.delete(); }
    }
}
