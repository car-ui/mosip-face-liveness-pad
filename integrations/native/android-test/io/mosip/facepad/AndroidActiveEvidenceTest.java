package io.mosip.facepad;

import static org.junit.Assert.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import android.content.Context;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.mosip.registration.clientmanager.constant.Modality;
import io.mosip.registration.clientmanager.dto.registration.BiometricsDto;
import io.mosip.registration.clientmanager.exception.BiometricsServiceException;
import io.mosip.registration.clientmanager.repository.GlobalParamRepository;
import io.mosip.registration.clientmanager.service.Biometrics095Service;
import io.mosip.registration.clientmanager.service.UserOnboardService;
import io.mosip.registration.clientmanager.spi.RegistrationService;
import io.mosip.registration.clientmanager.constant.RegistrationConstants;
import io.mosip.registration_client.api_services.BiometricsDetailsApi;
import io.mosip.registration_client.model.BiometricsPigeon;
import io.mosip.registration.clientmanager.spi.AuditManagerService;
import io.mosip.registration.keymanager.dto.JWTSignatureVerifyRequestDto;
import io.mosip.registration.keymanager.dto.JWTSignatureVerifyResponseDto;
import io.mosip.registration.keymanager.spi.ClientCryptoManagerService;
import io.mosip.registration.keymanager.util.KeyManagerConstant;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;

/** Real SBI parser + RSA verification through an explicit fixture crypto provider.
 * Trust is pinned to the generated fixture key. No production certificate chain is tested.
 */
@RunWith(AndroidJUnit4.class)
public class AndroidActiveEvidenceTest {
    private Context context;
    private byte[] iso;
    private String transaction;
    @Before public void setup() throws Exception {
        context=InstrumentationRegistry.getInstrumentation().getTargetContext();
        assertTrue(context.getSharedPreferences("facepad-evidence-v2",Context.MODE_PRIVATE).edit().clear().commit());
        transaction=UUID.randomUUID().toString();
        try(InputStream in=InstrumentationRegistry.getInstrumentation().getContext().getAssets().open("portrait-face.iso");
            ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            byte[] buffer=new byte[8192];int count;while((count=in.read(buffer))!=-1)out.write(buffer,0,count);iso=out.toByteArray();
        }
    }
    private JSONObject payload() throws Exception {
        long now=System.currentTimeMillis();
        JSONObject proof=new JSONObject().put("version",2).put("source","CAMERA2_JPEG_V2")
            .put("state","COMPLETE").put("actionCount",2).put("actionTypes",new JSONArray().put("BLINK").put("TURN_LEFT"))
            .put("transactionId",transaction)
            .put("padModelSha256",NativePadEngine.MODEL_SHA256)
            .put("landmarkModelSha256",NativeLandmarkEngine.MODEL_SHA256)
            .put("isoSha256",AndroidActiveEvidence.sha256(iso))
            .put("sessionStartedAtMillis",now-5000).put("sessionTimeoutMillis",20000)
            .put("retryLimit",2).put("retriesUsed",0).put("completedAtMillis",now-1000);
        return new JSONObject().put("bioType","Face").put("bioSubType","Face")
            .put("bioValue",Base64.getUrlEncoder().withoutPadding().encodeToString(iso))
            .put("transactionId",transaction).put("qualityScore",99).put("requestedScore","60")
            .put("timestamp",DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'").withZone(ZoneOffset.UTC).format(Instant.now()))
            .put("facePad",proof);
    }
    private BiometricsDto dto(JSONObject payload) throws Exception {
        BiometricsDto dto=new BiometricsDto();dto.setBioValue(payload.getString("bioValue"));
        dto.setDecodedBioResponse(payload.toString());dto.setModality("Face");return dto;
    }
    private void rejected(JSONObject value,String tx) throws Exception {
        try {AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,tx);fail("Invalid evidence accepted");}
        catch(IOException expected) {assertTrue(expected.getMessage().startsWith("PAD:"));}
    }
    @Test public void exactProofIsConsumedOnceAndPersisted() throws Exception {
        JSONObject value=payload();AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction);
        assertEquals(1,new JSONObject(context.getSharedPreferences("facepad-evidence-v2",0).getString("used","{}")).length());
        rejected(value,transaction);
    }
    @Test public void configuredActionCountMismatchDoesNotConsumeProof() throws Exception {
        NativePadPolicy policy=NativePadPolicy.read(key ->
            "mosip.facepad.operator.active.action_count".equals(key)?"3":null,
            NativePadPolicy.Workflow.OPERATOR);
        JSONObject value=payload();
        try {AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction,policy);fail("Wrong action count accepted");}
        catch(IOException expected) {assertTrue(expected.getMessage().contains("action count"));}
        assertEquals("{}",context.getSharedPreferences("facepad-evidence-v2",0).getString("used","{}"));
        value.getJSONObject("facePad").put("actionCount",3);
        value.getJSONObject("facePad").put("actionTypes",new JSONArray().put("BLINK").put("TURN_LEFT").put("BLINK"));
        AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction,policy);
        assertEquals(1,new JSONObject(context.getSharedPreferences("facepad-evidence-v2",0).getString("used","{}")).length());
        try {AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction,policy);fail("Replayed proof accepted");}
        catch(IOException expected) {assertTrue(expected.getMessage().contains("already consumed"));}
    }
    @Test public void unavailablePolicyCannotConsumeActiveProof() throws Exception {
        NativePadPolicy disabled=NativePadPolicy.read(key -> "mosip.facepad.enabled".equals(key)?"false":null,
            NativePadPolicy.Workflow.OPERATOR);
        for(NativePadPolicy policy:new NativePadPolicy[]{null,disabled}) {
            JSONObject value=payload();
            try {AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction,policy);fail("Unavailable policy accepted");}
            catch(IOException expected) {assertTrue(expected.getMessage().contains("current policy"));}
            assertEquals("{}",context.getSharedPreferences("facepad-evidence-v2",0).getString("used","{}"));
        }
    }
    @Test public void mandatoryWorkflowRequiresActiveEvidenceEvenAfterPassiveClear() throws Exception {
        NativePadEngine.Decision clear=new NativePadEngine.Decision(true,"PASSIVE_CLEAR",.99);
        NativePadEngine.Decision uncertain=new NativePadEngine.Decision(false,"ACTIVE_CHALLENGE_REQUIRED",.6);
        assertTrue(AndroidPadCheckpoint.requiresActiveEvidence(
            NativePadPolicy.defaults(NativePadPolicy.Workflow.OPERATOR),clear));
        assertTrue(AndroidPadCheckpoint.requiresActiveEvidence(
            NativePadPolicy.defaults(NativePadPolicy.Workflow.SUPERVISOR),clear));
        assertFalse(AndroidPadCheckpoint.requiresActiveEvidence(
            NativePadPolicy.defaults(NativePadPolicy.Workflow.RESIDENT),clear));
        assertTrue(AndroidPadCheckpoint.requiresActiveEvidence(
            NativePadPolicy.defaults(NativePadPolicy.Workflow.RESIDENT),uncertain));
    }
    @Test public void extraActionsSatisfyResidentMinimumButUnboundedCountsReject() throws Exception {
        JSONObject value=payload();
        value.getJSONObject("facePad").put("actionCount",5);
        try {AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction);fail("Unbounded action count accepted");}
        catch(IOException expected) {assertTrue(expected.getMessage().contains("action count"));}
        assertEquals("{}",context.getSharedPreferences("facepad-evidence-v2",0).getString("used","{}"));
        value.getJSONObject("facePad").put("actionCount",2);
        AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction,
            NativePadPolicy.defaults(NativePadPolicy.Workflow.RESIDENT));
        assertEquals(1,new JSONObject(context.getSharedPreferences("facepad-evidence-v2",0).getString("used","{}")).length());
    }
    @Test public void mismatchedIncompleteExpiredAndMalformedClaimsReject() throws Exception {
        String[] fields={"isoSha256","transactionId","padModelSha256","landmarkModelSha256","state","source","actionTypes"};
        for(String field:fields) {JSONObject value=payload();value.getJSONObject("facePad").put(field,"wrong");rejected(value,transaction);}
        for(long timestamp:new long[]{System.currentTimeMillis()-31000,System.currentTimeMillis()+10000}) {
            JSONObject value=payload();JSONObject proof=value.getJSONObject("facePad");
            proof.put("completedAtMillis",timestamp).put("sessionStartedAtMillis",timestamp-4000);
            rejected(value,transaction);
        }
        JSONObject value=payload();value.getJSONObject("facePad").put("actionCount",1);rejected(value,transaction);
        value=payload();value.getJSONObject("facePad").put("version","1");rejected(value,transaction);
        value=payload();value.getJSONObject("facePad").put("sessionStartedAtMillis",value.getJSONObject("facePad").getLong("completedAtMillis")+1);rejected(value,transaction);
        value=payload();value.getJSONObject("facePad").put("sessionTimeoutMillis",500);rejected(value,transaction);
        value=payload();value.getJSONObject("facePad").put("retryLimit",0).put("retriesUsed",1);rejected(value,transaction);
        value=payload();value.remove("facePad");rejected(value,transaction);
        rejected(payload(),null);rejected(payload(),"other-transaction");
        value=payload();BiometricsDto mismatch=dto(value);mismatch.setBioValue("AA");
        try {AndroidActiveEvidence.verifyAndConsume(context,mismatch,iso,transaction);fail("DTO mismatch accepted");}catch(IOException expected){}
    }
    @Test public void timeoutAndRecoveryClaimsMustFitCurrentPolicy() throws Exception {
        NativePadPolicy restrictive=NativePadPolicy.read(key -> {
            if("mosip.facepad.operator.active.timeout_seconds".equals(key))return "5";
            if("mosip.facepad.operator.active.max_retries".equals(key))return "0";
            return null;
        },NativePadPolicy.Workflow.OPERATOR);
        JSONObject value=payload();
        value.getJSONObject("facePad").put("sessionStartedAtMillis",
            value.getJSONObject("facePad").getLong("completedAtMillis")-7000);
        try {AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction,restrictive);fail("Long session accepted under short timeout");}
        catch(IOException expected) {assertTrue(expected.getMessage().contains("policy timeout"));}
        value=payload();JSONObject proof=value.getJSONObject("facePad");
        proof.put("sessionStartedAtMillis",proof.getLong("completedAtMillis")-4000);
        proof.put("retriesUsed",1);
        try {AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction,restrictive);fail("Retry accepted under zero-retry policy");}
        catch(IOException expected) {assertTrue(expected.getMessage().contains("retry policy"));}
        proof.put("retriesUsed",0);
        AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction,restrictive);
    }
    @Test public void challengeTypesMustBelongToCurrentPolicyPool() throws Exception {
        NativePadPolicy blinkOnly=NativePadPolicy.read(key ->
            "mosip.facepad.operator.active.challenge_types".equals(key)?"blink":null,
            NativePadPolicy.Workflow.OPERATOR);
        JSONObject value=payload();
        try {AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction,blinkOnly);fail("Turn outside configured challenge pool accepted");}
        catch(IOException expected) {assertTrue(expected.getMessage().contains("challenge type"));}
        value.getJSONObject("facePad").put("actionTypes",new JSONArray().put("BLINK").put("BLINK"));
        AndroidActiveEvidence.verifyAndConsume(context,dto(value),iso,transaction,blinkOnly);
    }
    @Test public void clockRollbackAndFullLedgerReject() throws Exception {
        android.content.SharedPreferences storage=context.getSharedPreferences("facepad-evidence-v2",0);
        assertTrue(storage.edit().putLong("clock",System.currentTimeMillis()+10000).commit());rejected(payload(),transaction);
        JSONObject ledger=new JSONObject();for(int i=0;i<256;i++)ledger.put("used-"+i,System.currentTimeMillis()+120000);
        assertTrue(storage.edit().putLong("clock",0).putString("used",ledger.toString()).commit());rejected(payload(),transaction);
    }
    @Test public void persistenceFailureCannotAcceptEvidence() throws Exception {
        Context failing=mock(Context.class);
        android.content.SharedPreferences storage=mock(android.content.SharedPreferences.class);
        android.content.SharedPreferences.Editor editor=mock(android.content.SharedPreferences.Editor.class,RETURNS_SELF);
        when(failing.getSharedPreferences("facepad-evidence-v2",0)).thenReturn(storage);
        when(storage.getString("used","{}")).thenReturn("{}");when(storage.edit()).thenReturn(editor);
        when(editor.commit()).thenReturn(false);
        try {AndroidActiveEvidence.verifyAndConsume(failing,dto(payload()),iso,transaction);fail("Unpersisted proof accepted");}
        catch(IOException expected) {assertTrue(expected.getMessage().contains("persisted"));}
    }
    @Test public void activeMetadataCannotOverrideNoFaceDecision() throws Exception {
        byte[] blank;
        try(InputStream in=InstrumentationRegistry.getInstrumentation().getContext().getAssets().open("blank-face.iso");
            ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            byte[] buffer=new byte[8192];int count;while((count=in.read(buffer))!=-1)out.write(buffer,0,count);blank=out.toByteArray();
        }
        JSONObject value=payload();value.put("bioValue",encode(blank));value.getJSONObject("facePad").put("isoSha256",AndroidActiveEvidence.sha256(blank));
        try {AndroidPadCheckpoint.requireClear(context,Collections.singletonList(dto(value)),true,transaction);fail("No-face capture accepted");}
        catch(IOException expected) {assertTrue(expected.getMessage().contains("NO_FACE"));}
        assertEquals("{}",context.getSharedPreferences("facepad-evidence-v2",0).getString("used","{}"));
    }
    private static String encode(byte[] bytes) {return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);}
    private static String sign(JSONObject payload,KeyPair keys) throws Exception {
        String body=encode("{\"alg\":\"RS256\"}".getBytes(StandardCharsets.UTF_8))+"."+encode(payload.toString().getBytes(StandardCharsets.UTF_8));
        Signature signer=Signature.getInstance("SHA256withRSA");signer.initSign(keys.getPrivate());signer.update(body.getBytes(StandardCharsets.UTF_8));
        return body+"."+encode(signer.sign());
    }
    private List<BiometricsDto> parse(Biometrics095Service service,String jwt,String tx) throws Exception {
        return service.handleRCaptureResponse(Modality.FACE,new ByteArrayInputStream(response(jwt)),Collections.emptyList(),tx,true);
    }
    private byte[] response(String jwt) throws Exception {
        JSONObject capture=new JSONObject().put("specVersion","0.9.5").put("data",jwt)
            .put("error",new JSONObject().put("errorCode","0").put("errorInfo","Success"));
        return new JSONObject().put("biometrics",new JSONArray().put(capture)).toString().getBytes(StandardCharsets.UTF_8);
    }
    private void exerciseActualOnboardingPadVeto(Biometrics095Service service,String jwt) throws Exception {
        List<BiometricsDto> stored=new ArrayList<>();
        UserOnboardService onboarding=mock(UserOnboardService.class);
        when(onboarding.getCaptureTransactionId()).thenReturn(transaction);
        when(onboarding.getOperatorBiometrics()).thenReturn(stored);
        android.app.Activity activity=mock(android.app.Activity.class);
        when(activity.getApplicationContext()).thenReturn(context);
        when(activity.getContentResolver()).thenReturn(context.getContentResolver());
        when(activity.getAssets()).thenReturn(context.getAssets());
        when(activity.getCacheDir()).thenReturn(context.getCacheDir());
        when(activity.getSharedPreferences(anyString(),anyInt())).thenAnswer(call -> context.getSharedPreferences(call.getArgument(0),call.getArgument(1)));
        BiometricsDetailsApi api=new BiometricsDetailsApi(mock(AuditManagerService.class),new ObjectMapper(),service,
            mock(RegistrationService.class),mock(GlobalParamRepository.class),onboarding);
        for(Object[] field:new Object[][]{{"activity",activity},{"currentModality",Modality.FACE},{"fieldId","operatorBiometrics"}}) {
            java.lang.reflect.Field member=BiometricsDetailsApi.class.getDeclaredField((String)field[0]);member.setAccessible(true);member.set(api,field[1]);
        }
        AtomicReference<Throwable> failure=new AtomicReference<>();AtomicReference<String> success=new AtomicReference<>();
        BiometricsPigeon.Result<String> callback=new BiometricsPigeon.Result<String>() {
            public void success(String value) {success.set(value);}
            public void error(Throwable error) {failure.set(error);}
        };
        java.lang.reflect.Field callbackField=BiometricsDetailsApi.class.getDeclaredField("biometricResult");
        callbackField.setAccessible(true);callbackField.set(api,callback);
        File file=File.createTempFile("signed-pad-fixture-",".json",context.getCacheDir());
        try {
            try(FileOutputStream output=new FileOutputStream(file)) {output.write(response(jwt));}
            android.os.Bundle bundle=new android.os.Bundle();bundle.putParcelable(RegistrationConstants.SBI_INTENT_RESPONSE_KEY,android.net.Uri.fromFile(file));
            InstrumentationRegistry.getInstrumentation().runOnMainSync(() -> api.parseRCaptureResponse(bundle));
            assertNull(success.get());assertNotNull(failure.get());assertEquals(0,stored.size());
            assertTrue(failure.get().getMessage(),failure.get().getMessage().contains("PRESENTATION_ATTACK"));
            success.set(null);
            InstrumentationRegistry.getInstrumentation().runOnMainSync(() -> api.parseRCaptureResponse(bundle));
            assertNull(success.get());assertNotNull(failure.get());assertEquals(0,stored.size());
        } finally {file.delete();}
    }
    @Test public void realParserVerifiesRsaBeforeActiveCheckpointAndRejectsTampering() throws Exception {
        KeyPairGenerator generator=KeyPairGenerator.getInstance("RSA");generator.initialize(2048);KeyPair keys=generator.generateKeyPair();
        AtomicBoolean trusted=new AtomicBoolean(true);
        ClientCryptoManagerService crypto=mock(ClientCryptoManagerService.class);
        when(crypto.jwtVerify(any(JWTSignatureVerifyRequestDto.class))).thenAnswer(call -> {
            JWTSignatureVerifyRequestDto request=call.getArgument(0);
            assertEquals(Boolean.TRUE,request.getValidateTrust());assertEquals("DEVICE",request.getDomain());
            String[] parts=request.getJwtSignatureData().split("\\.");
            Signature verifier=Signature.getInstance("SHA256withRSA");verifier.initVerify(keys.getPublic());
            verifier.update((parts[0]+"."+parts[1]).getBytes(StandardCharsets.UTF_8));
            JWTSignatureVerifyResponseDto result=new JWTSignatureVerifyResponseDto();
            result.setSignatureValid(verifier.verify(Base64.getUrlDecoder().decode(parts[2])));
            result.setTrustValid(trusted.get()?KeyManagerConstant.TRUST_VALID:"UNTRUSTED");return result;
        });
        Biometrics095Service service=new Biometrics095Service(context,new ObjectMapper(),mock(AuditManagerService.class),
            mock(GlobalParamRepository.class),crypto,null,null);
        JSONObject value=payload();String jwt=sign(value,keys);
        List<BiometricsDto> verified=parse(service,jwt,transaction);
        assertEquals(1,verified.size());
        exerciseActualOnboardingPadVeto(service,jwt);
        try {AndroidPadCheckpoint.requireClear(context,verified,true,transaction);fail("Signed metadata overrode PAD attack");}
        catch(IOException expected) {assertTrue(expected.getMessage(),expected.getMessage().contains("PRESENTATION_ATTACK"));}
        String[] parts=jwt.split("\\.");value.getJSONObject("facePad").put("state","INCOMPLETE");
        String tampered=parts[0]+"."+encode(value.toString().getBytes(StandardCharsets.UTF_8))+"."+parts[2];
        try {parse(service,tampered,transaction);fail("Tampered signature accepted");}catch(BiometricsServiceException expected){}
        trusted.set(false);
        try {parse(service,jwt,transaction);fail("Untrusted fixture accepted");}catch(BiometricsServiceException expected){}
        trusted.set(true);
        try {parse(service,jwt,"wrong-transaction");fail("Wrong transaction accepted");}catch(BiometricsServiceException expected){}
    }
}
