package io.mosip.facepad;

import java.io.IOException;
import org.json.JSONObject;

/** Metadata for the exact ISO generated after consuming the camera session's proof.
 * The SBI must include this object inside its signed capture payload.
 */
public final class CameraActiveEvidence {
    private CameraActiveEvidence() { }
    public static String completed(byte[] iso,String transactionId) throws Exception {
        if(transactionId==null || transactionId.isEmpty() || transactionId.length()>128)
            throw new IOException("Capture transaction is required");
        return new JSONObject().put("version",1).put("source","CAMERA2_JPEG_V1")
            .put("state","COMPLETE").put("actionCount",2).put("transactionId",transactionId)
            .put("padModelSha256",NativePadEngine.MODEL_SHA256)
            .put("landmarkModelSha256",NativeLandmarkEngine.MODEL_SHA256)
            .put("isoSha256",NativePadEngine.sha256(iso))
            .put("completedAtMillis",System.currentTimeMillis()).toString();
    }
}
