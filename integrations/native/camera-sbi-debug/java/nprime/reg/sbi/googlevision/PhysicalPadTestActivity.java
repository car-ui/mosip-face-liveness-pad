package nprime.reg.sbi.googlevision;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.View;
import android.view.WindowManager;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import io.mosip.facepad.NativePadEngine;
import io.mosip.facepad.NativeLandmarkEngine;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import org.json.*;

/** Debug-only camera trials. No signing credentials, registration or identity matching. */
public final class PhysicalPadTestActivity extends AppCompatActivity {
    private static final String[] CASES={"bona_fide","printed_photo","screen_replay","other_attack"};
    private static final String[] LABELS={"Real person","Printed face photo","Face video on another screen","Other attack"};
    private static final int CAPTURE=73,EXPORT=74;
    private final ArrayList<JSONObject> trials=new ArrayList<>();
    private TextView result;
    private Spinner scenario;
    private Button start;
    private String transaction,pendingCase;
    private long started;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);
        int margin=(int)(16*getResources().getDisplayMetrics().density);layout.setPadding(margin,margin,margin,margin);
        TextView title=new TextView(this);title.setTextSize(22);title.setText("Native PAD physical trial");layout.addView(title);
        TextView scope=new TextView(this);scope.setText("Debug camera test only. This does not register or authenticate anyone. Choose the actual presentation before starting. Reports contain outcomes and model hashes, without images or identities.");layout.addView(scope);
        scenario=new Spinner(this);scenario.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,LABELS));layout.addView(scenario);
        start=new Button(this);start.setText("Start camera trial");start.setOnClickListener(v -> startTrial());layout.addView(start);
        Button export=new Button(this);export.setText("Export anonymous report");export.setOnClickListener(v -> export());layout.addView(export);
        result=new TextView(this);result.setTextSize(18);result.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);layout.addView(result);
        setContentView(layout);
        if(state!=null) {
            transaction=state.getString("transaction");pendingCase=state.getString("case");started=state.getLong("started");
            start.setEnabled(transaction==null);
        }
        try {load();show();}catch(Exception failure) {result.setText("Saved report could not be loaded. Export or clear app data before new trials.");start.setEnabled(false);}
    }
    @Override protected void onSaveInstanceState(Bundle state) {
        state.putString("transaction",transaction);state.putString("case",pendingCase);state.putLong("started",started);super.onSaveInstanceState(state);
    }
    void startTrial() {
        if(transaction!=null || trials.size()>=1000)return;
        pendingCase=CASES[scenario.getSelectedItemPosition()];transaction=UUID.randomUUID().toString();started=SystemClock.elapsedRealtime();start.setEnabled(false);
        Intent intent=new Intent(this,NativePadCameraActivity.class);
        intent.putExtra("FacePadTransactionId",transaction);intent.putExtra("CaptureTimeout",30000);intent.putExtra("QualityThreshold",60);
        startActivityForResult(intent,CAPTURE);
    }
    @Override protected void onActivityResult(int request,int code,Intent data) {
        super.onActivityResult(request,code,data);
        if(request==EXPORT) {
            if(code==Activity.RESULT_OK && data!=null && data.getData()!=null)try {
                try(OutputStream stream=getContentResolver().openOutputStream(data.getData())) {
                    if(stream==null)throw new IOException("No output stream");stream.write(report().toString(2).getBytes(StandardCharsets.UTF_8));
                }
                result.setText("Anonymous report exported. No images were included.");
            }catch(Exception failure) {result.setText("Report export failed. The local report is still available.");}
            return;
        }
        if(request!=CAPTURE || transaction==null)return;
        try {
            JSONObject trial=summarize(code,data,transaction,pendingCase,Math.max(0,SystemClock.elapsedRealtime()-started));
            trials.add(trial);persist();show();
        }catch(Exception failure) {result.setText("Trial could not be recorded. Do not count it as a pass.");start.setEnabled(false);return;}
        finally {transaction=null;pendingCase=null;}
        start.setEnabled(trials.size()<1000);
    }
    static JSONObject summarize(int code,Intent data,String transaction,String label,long elapsed) throws Exception {
        boolean accepted=false;String reason="CAPTURE_CANCELLED_OR_FAILED";
        if(code==Activity.RESULT_OK && data!=null && data.getIntExtra("Status",-1)==0) {
            byte[] iso=data.getByteArrayExtra("IsoFaceRecord");String raw=data.getStringExtra("FacePadEvidence");
            if(iso!=null && iso.length>0 && iso.length<=8*1024*1024 && raw!=null && raw.length()<4096) {
                JSONObject proof=new JSONObject(raw);long now=System.currentTimeMillis();
                accepted="COMPLETE".equals(proof.opt("state")) && "CAMERA2_JPEG_V1".equals(proof.opt("source"))
                    && proof.optInt("version")==1 && proof.optInt("actionCount")==2
                    && transaction.equals(proof.opt("transactionId"))
                    && NativePadEngine.MODEL_SHA256.equals(proof.opt("padModelSha256"))
                    && NativeLandmarkEngine.MODEL_SHA256.equals(proof.opt("landmarkModelSha256"))
                    && digest(iso).equals(proof.opt("isoSha256"))
                    && proof.optLong("completedAtMillis")>=now-30000 && proof.optLong("completedAtMillis")<=now+2000;
            }
            reason=accepted?"NATIVE_CAMERA_ACCEPTED":"INVALID_COMPLETED_EVIDENCE";
        }
        return new JSONObject().put("presentation",label).put("accepted",accepted).put("reason",reason)
            .put("outcome",accepted?"accepted":"capture_failed_or_incomplete").put("elapsedMs",elapsed);
    }
    private static String digest(byte[] bytes) throws Exception {
        StringBuilder out=new StringBuilder(64);for(byte b:MessageDigest.getInstance("SHA-256").digest(bytes))out.append(String.format(Locale.ROOT,"%02x",b&255));return out.toString();
    }
    private File store() {return new File(getFilesDir(),"physical-pad-trials.json");}
    private JSONObject report() throws Exception {
        return new JSONObject().put("scope","Debug native camera trials; no registration, authentication, production PKI or ISO accuracy certification")
            .put("deviceModel",android.os.Build.MODEL).put("manufacturer",android.os.Build.MANUFACTURER)
            .put("androidApi",android.os.Build.VERSION.SDK_INT)
            .put("padModelSha256",NativePadEngine.MODEL_SHA256).put("landmarkModelSha256",NativeLandmarkEngine.MODEL_SHA256)
            .put("qualityThreshold",60).put("captureTimeoutMs",30000).put("trials",new JSONArray(trials));
    }
    private void persist() throws Exception {
        File temporary=new File(getFilesDir(),"physical-pad-trials.tmp");
        try(FileOutputStream stream=new FileOutputStream(temporary)) {stream.write(report().toString().getBytes(StandardCharsets.UTF_8));stream.getFD().sync();}
        if(!temporary.renameTo(store()))throw new IOException("Report write failed");
    }
    private void load() throws Exception {
        if(!store().exists())return;
        if(store().length()>1024*1024)throw new IOException("Report too large");
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();try(InputStream in=new FileInputStream(store())) {byte[] block=new byte[4096];int n;while((n=in.read(block))!=-1)bytes.write(block,0,n);}
        JSONArray saved=new JSONObject(bytes.toString("UTF-8")).getJSONArray("trials");if(saved.length()>1000)throw new IOException("Too many trials");
        for(int i=0;i<saved.length();i++)trials.add(saved.getJSONObject(i));
    }
    private void show() throws Exception {
        if(trials.isEmpty()) {result.setText("No physical trials recorded.");return;}
        JSONObject last=trials.get(trials.size()-1);
        result.setText("Trials: "+trials.size()+"\nLast presentation: "+last.getString("presentation")+"\nCapture accepted: "+last.getBoolean("accepted")+"\nReason: "+last.getString("reason"));
    }
    private void export() {
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);intent.setType("application/json");intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.putExtra(Intent.EXTRA_TITLE,"native-pad-physical-trials.json");startActivityForResult(intent,EXPORT);
    }
}
