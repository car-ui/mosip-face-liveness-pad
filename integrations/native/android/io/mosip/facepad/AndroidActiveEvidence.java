package io.mosip.facepad;

import android.content.Context;
import android.content.SharedPreferences;
import io.mosip.registration.clientmanager.dto.registration.BiometricsDto;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Iterator;
import org.json.JSONObject;

/** Consumes only the decoded payload returned by the existing trusted SBI validator.
 * This class does not authenticate a DTO. Its caller must first verify SBI signature,
 * certificate trust, timestamp and the current capture transaction through MOSIP.
 */
public final class AndroidActiveEvidence {
    private static final long MAX_AGE_MS=30000, SKEW_MS=2000, RETAIN_MS=120000;
    private AndroidActiveEvidence() { }

    public static synchronized void verifyAndConsume(Context context, BiometricsDto biometric,
                                                     byte[] iso, String expectedTransaction) throws IOException {
        try {
            if(expectedTransaction==null || expectedTransaction.isEmpty() || expectedTransaction.length()>128)
                throw new IOException("PAD: current capture transaction is required");
            String decoded=biometric.getDecodedBioResponse();
            if(decoded==null || decoded.length()>12*1024*1024 || iso==null || iso.length>8*1024*1024)
                throw new IOException("PAD: signed capture payload unavailable");
            JSONObject payload=new JSONObject(decoded);
            require(expectedTransaction.equals(payload.opt("transactionId")),"capture transaction mismatch");
            require(biometric.getBioValue().equals(payload.opt("bioValue")),"capture value mismatch");
            JSONObject proof=payload.getJSONObject("facePad");
            require(integer(proof,"version")==1,"unsupported active proof version");
            require("CAMERA2_JPEG_V1".equals(proof.opt("source")),"unsupported active proof source");
            require("COMPLETE".equals(proof.opt("state")),"active challenge incomplete");
            require(integer(proof,"actionCount")==2,"active challenge actions missing");
            require(expectedTransaction.equals(proof.opt("transactionId")),"active transaction mismatch");
            require(NativePadEngine.MODEL_SHA256.equals(proof.opt("padModelSha256")),"PAD model mismatch");
            require(NativeLandmarkEngine.MODEL_SHA256.equals(proof.opt("landmarkModelSha256")),"landmark model mismatch");
            require(sha256(iso).equals(proof.opt("isoSha256")),"active capture digest mismatch");
            long completed=integer(proof,"completedAtMillis"),now=System.currentTimeMillis();
            require(completed>0 && completed<=now+SKEW_MS && completed>=now-MAX_AGE_MS,"active proof expired");

            SharedPreferences storage=context.getSharedPreferences("facepad-evidence-v1",Context.MODE_PRIVATE);
            long previousClock=storage.getLong("clock",0);
            require(now>=previousClock-SKEW_MS,"clock moved backwards");
            JSONObject ledger=new JSONObject(storage.getString("used","{}"));
            Iterator<String> keys=ledger.keys();
            while(keys.hasNext()) {String key=keys.next();if(ledger.getLong(key)<now)keys.remove();}
            String token=sha256(expectedTransaction.getBytes(StandardCharsets.UTF_8));
            require(!ledger.has(token),"active proof already consumed");
            require(ledger.length()<256,"active proof ledger full");
            ledger.put(token,now+RETAIN_MS);
            require(storage.edit().putString("used",ledger.toString()).putLong("clock",Math.max(now,previousClock)).commit(),"active proof could not be persisted");
        } catch(IOException failure) {throw failure;}
        catch(Exception failure) {throw new IOException("PAD: invalid signed active evidence",failure);}
    }

    private static long integer(JSONObject value,String key) throws Exception {
        Object field=value.get(key);
        require(field instanceof Integer || field instanceof Long,"invalid numeric proof field");
        return ((Number)field).longValue();
    }
    private static void require(boolean valid,String reason) throws IOException {
        if(!valid)throw new IOException("PAD: "+reason);
    }
    static String sha256(byte[] bytes) throws Exception {
        byte[] digest=MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder value=new StringBuilder(64);
        for(byte element:digest)value.append(String.format(java.util.Locale.ROOT,"%02x",element & 255));
        return value.toString();
    }
}
