package io.mosip.facepad;

import java.io.IOException;
import org.json.JSONObject;

/** Metadata for the exact ISO generated after consuming the camera session's proof.
 * The SBI must include this object inside its signed capture payload.
 */
public final class CameraActiveEvidence {
    private CameraActiveEvidence() { }
    public static String completed(byte[] iso,String transactionId,NativeActiveSession.Attestation session) throws Exception {
        if(transactionId==null || transactionId.isEmpty() || transactionId.length()>128)
            throw new IOException("Capture transaction is required");
        if(iso==null || iso.length==0 || iso.length>8*1024*1024 || session==null
                || session.sessionStartedAtMillis<=0 || session.completedAtMillis<session.sessionStartedAtMillis
                || session.sessionTimeoutMillis<1000 || session.sessionTimeoutMillis>60000
                || session.actionCount<1 || session.actionCount>4 || session.retryLimit<0 || session.retryLimit>5
                || session.retriesUsed<0 || session.retriesUsed>session.retryLimit)
            throw new IOException("Completed camera session evidence is invalid");
        return new JSONObject().put("version",2).put("source","CAMERA2_JPEG_V2")
            .put("state","COMPLETE").put("actionCount",session.actionCount).put("transactionId",transactionId)
            .put("actionTypes",new org.json.JSONArray(java.util.Arrays.asList(session.actionTypes())))
            .put("padModelSha256",NativePadEngine.MODEL_SHA256)
            .put("landmarkModelSha256",NativeLandmarkEngine.MODEL_SHA256)
            .put("isoSha256",NativePadEngine.sha256(iso))
            .put("sessionStartedAtMillis",session.sessionStartedAtMillis)
            .put("sessionTimeoutMillis",session.sessionTimeoutMillis)
            .put("retryLimit",session.retryLimit).put("retriesUsed",session.retriesUsed)
            .put("completedAtMillis",session.completedAtMillis).toString();
    }
}
