package nprime.reg.sbi.googlevision;

import static org.junit.Assert.*;
import android.app.Activity;
import android.content.Intent;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import io.mosip.facepad.CameraActiveEvidence;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;

/** Debug launcher only; fabricated completion metadata is not a human camera trial. */
@RunWith(AndroidJUnit4.class)
public class PhysicalPadHarnessTest {
    @Test public void debugLauncherOpensWithoutProvisioningOrCameraAccess() throws Exception {
        try(ActivityScenario<PhysicalPadTestActivity> screen=ActivityScenario.launch(PhysicalPadTestActivity.class)) {
            screen.onActivity(activity -> {
                assertNotNull(activity.getWindow().getDecorView());
                assertFalse(activity.isFinishing());
            });
        }
    }
    @Test public void reportCannotAcceptFlagsWithoutExactCurrentEvidence() throws Exception {
        Intent result=new Intent();result.putExtra("Status",0);result.putExtra("IsoFaceRecord",new byte[]{1,2,3});
        assertFalse(PhysicalPadTestActivity.summarize(Activity.RESULT_OK,result,"tx","bona_fide",1).getBoolean("accepted"));
        result.putExtra("FacePadEvidence",CameraActiveEvidence.completed(new byte[]{1,2,3},"tx"));
        JSONObject summary=PhysicalPadTestActivity.summarize(Activity.RESULT_OK,result,"tx","bona_fide",2);
        assertTrue(summary.getBoolean("accepted"));assertFalse(summary.has("IsoFaceRecord"));assertFalse(summary.has("transactionId"));
        assertFalse(PhysicalPadTestActivity.summarize(Activity.RESULT_OK,result,"different-tx","bona_fide",2).getBoolean("accepted"));
        result.putExtra("IsoFaceRecord",new byte[]{9,8,7});
        assertFalse(PhysicalPadTestActivity.summarize(Activity.RESULT_OK,result,"tx","bona_fide",2).getBoolean("accepted"));
        assertEquals("capture_failed_or_incomplete",PhysicalPadTestActivity.summarize(Activity.RESULT_CANCELED,null,"tx","printed_photo",2).getString("outcome"));
    }
}
