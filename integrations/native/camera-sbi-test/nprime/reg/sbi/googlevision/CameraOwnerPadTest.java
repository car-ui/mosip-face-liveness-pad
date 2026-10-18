package nprime.reg.sbi.googlevision;

import static org.junit.Assert.*;
import android.app.Activity;
import android.app.Instrumentation;
import android.content.Context;
import android.content.Intent;
import android.graphics.*;
import android.media.ExifInterface;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import io.mosip.facepad.CameraOwnedPadGate;
import io.mosip.facepad.CameraActiveEvidence;
import io.mosip.facepad.NativePadEngine;
import io.mosip.facepad.NativeLandmarkEngine;
import org.json.JSONObject;
import io.mosip.facepad.NativeActiveSession;
import java.io.*;
import java.nio.file.Files;
import npr.util.BioFace;
import org.junit.Test;
import org.junit.runner.RunWith;

/** Actual reference SBI/native engines; camera disabled on the isolated emulator. */
@RunWith(AndroidJUnit4.class)
public class CameraOwnerPadTest {
    @Test public void activeMetadataBindsIsoModelsAndTransaction() throws Exception {
        byte[] iso=new byte[]{1,2,3};
        JSONObject proof=new JSONObject(CameraActiveEvidence.completed(iso,"fixture-transaction"));
        assertEquals("fixture-transaction",proof.getString("transactionId"));
        assertEquals("039058c6f2c0cb492c533b0a4d14ef77cc0f78abccced5287d84a1a2011cfb81",proof.getString("isoSha256"));
        assertEquals(NativePadEngine.MODEL_SHA256,proof.getString("padModelSha256"));
        assertEquals(NativeLandmarkEngine.MODEL_SHA256,proof.getString("landmarkModelSha256"));
        assertEquals(2,proof.getInt("actionCount"));
        assertTrue(Math.abs(System.currentTimeMillis()-proof.getLong("completedAtMillis"))<2000);
        try {CameraActiveEvidence.completed(iso,null);fail("Missing transaction accepted");}catch(IOException expected){}
    }
    private Context target() { return InstrumentationRegistry.getInstrumentation().getTargetContext(); }
    private byte[] portrait() throws Exception {
        Bitmap image;
        try(InputStream stream=InstrumentationRegistry.getInstrumentation().getContext().getAssets().open("astronaut.png")) {
            image=BitmapFactory.decodeStream(stream);
        }
        try(ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            assertTrue(image.compress(Bitmap.CompressFormat.JPEG,90,out));return out.toByteArray();
        } finally { image.recycle(); }
    }
    @Test public void blankAndRepeatedStaticFramesCannotSupplyActiveProof() throws Exception {
        Bitmap image=Bitmap.createBitmap(640,480,Bitmap.Config.ARGB_8888);
        byte[] blank;
        try(ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            image.compress(Bitmap.CompressFormat.JPEG,90,out);blank=out.toByteArray();
        } finally { image.recycle(); }
        try(CameraOwnedPadGate gate=new CameraOwnedPadGate(target(),60000)) {
            assertEquals(NativeActiveSession.State.VERIFYING,gate.observe(blank));
            assertFalse(gate.consume(blank));
            byte[] photo=NativePadCameraActivity.normalize(portrait());
            for(int i=0;i<12;i++)assertNotEquals(NativeActiveSession.State.COMPLETE,gate.observe(photo));
            assertFalse(gate.consume(photo));
            assertEquals(0,NativePadCameraActivity.frameQuality(blank));
        }
    }
    @Test public void closedCameraSessionCannotAcceptFrames() throws Exception {
        CameraOwnedPadGate gate=new CameraOwnedPadGate(target(),10000);gate.close();gate.close();
        assertFalse(gate.consume(portrait()));
        try { gate.observe(portrait());fail("Closed gate accepted input"); }
        catch(IOException expected) { assertTrue(expected.getMessage().contains("closed")); }
    }
    @Test public void isoEncoderPreservesExactJpegBytes() throws Exception {
        byte[] jpeg=NativePadCameraActivity.normalize(portrait());
        BitmapFactory.Options shape=new BitmapFactory.Options();shape.inJustDecodeBounds=true;
        BitmapFactory.decodeByteArray(jpeg,0,jpeg.length,shape);
        byte[] iso=BioFace.generateFaceISO2011(jpeg,shape.outHeight,shape.outWidth,"00");
        assertTrue(BioFace.isFaceISO2011Valid(iso));
        assertArrayEquals(jpeg,BioFace.getFaceImageFromISO2011(iso));
    }
    @Test public void allExifOrientationsNormalizeRasterAndStripMetadata() throws Exception {
        Bitmap image=Bitmap.createBitmap(120,80,Bitmap.Config.ARGB_8888);
        Canvas canvas=new Canvas(image);Paint paint=new Paint();
        int[] colors={Color.RED,Color.GREEN,Color.BLUE,Color.YELLOW};
        for(int i=0;i<4;i++) {paint.setColor(colors[i]);canvas.drawRect((i%2)*60,(i/2)*40,(i%2+1)*60,(i/2+1)*40,paint);}
        byte[] raw;
        try(ByteArrayOutputStream out=new ByteArrayOutputStream()) {image.compress(Bitmap.CompressFormat.JPEG,95,out);raw=out.toByteArray();}
        finally {image.recycle();}
        int[] topLeft={0,0,1,3,2,0,2,3,1};
        for(int orientation=1;orientation<=8;orientation++) {
            File source=File.createTempFile("orientation-", ".jpg",target().getCacheDir());
            try {
                Files.write(source.toPath(),raw);
                ExifInterface exif=new ExifInterface(source.getAbsolutePath());
                exif.setAttribute(ExifInterface.TAG_ORIENTATION,Integer.toString(orientation));exif.saveAttributes();
                byte[] normalized=NativePadCameraActivity.normalize(Files.readAllBytes(source.toPath()));
                Bitmap result=BitmapFactory.decodeByteArray(normalized,0,normalized.length);
                try {
                    assertEquals(orientation>=5?80:120,result.getWidth());
                    assertEquals(orientation>=5?120:80,result.getHeight());
                    int expected=colors[topLeft[orientation]],actual=result.getPixel(10,10);
                    assertTrue(Math.abs(Color.red(expected)-Color.red(actual))<25);
                    assertTrue(Math.abs(Color.green(expected)-Color.green(actual))<25);
                    assertTrue(Math.abs(Color.blue(expected)-Color.blue(actual))<25);
                    ExifInterface cleaned=new ExifInterface(new ByteArrayInputStream(normalized));
                    int normalizedOrientation=cleaned.getAttributeInt(ExifInterface.TAG_ORIENTATION,0);
                    assertTrue("Normalized JPEG must not request another transform",normalizedOrientation==0 || normalizedOrientation==1);
                } finally {result.recycle();}
            } finally {source.delete();}
        }
    }
    @Test public void noCameraCannotReturnAnIsoCapture() throws Exception {
        android.hardware.camera2.CameraManager cameras=(android.hardware.camera2.CameraManager)target().getSystemService(Context.CAMERA_SERVICE);
        assertEquals("This check requires the documented camera-disabled emulator",0,cameras.getCameraIdList().length);
        Intent intent=new Intent(target(),NativePadCameraActivity.class);intent.putExtra("CaptureTimeout",1500);
        try(ActivityScenario<NativePadCameraActivity> scenario=ActivityScenario.launchActivityForResult(intent)) {
            Instrumentation.ActivityResult result=scenario.getResult();
            assertEquals(Activity.RESULT_CANCELED,result.getResultCode());
            assertNotNull(result.getResultData());
            assertEquals(0,result.getResultData().getByteArrayExtra("IsoFaceRecord").length);
        }
    }
}
