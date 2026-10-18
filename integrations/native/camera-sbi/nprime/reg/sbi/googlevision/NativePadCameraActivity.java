package nprime.reg.sbi.googlevision;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.*;
import android.hardware.camera2.*;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.ImageReader;
import android.os.*;
import android.util.Size;
import android.view.Surface;
import android.view.WindowManager;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import io.mosip.facepad.CameraOwnedPadGate;
import io.mosip.facepad.CameraActiveEvidence;
import io.mosip.facepad.NativeActiveSession;
import java.io.*;
import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import npr.util.BioFace;
import nprime.reg.sbi.faceCaptureApi.FaceCaptureResult;
import org.opencv.core.*;
import org.opencv.imgcodecs.Imgcodecs;
import org.opencv.imgproc.Imgproc;

/** Camera-owning research SBI path. Final ISO contains the exact verified JPEG. */
public final class NativePadCameraActivity extends AppCompatActivity {
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final AtomicBoolean finished = new AtomicBoolean();
    private final AtomicBoolean previewPending = new AtomicBoolean();
    private HandlerThread worker;
    private Handler background;
    private volatile CameraDevice camera;
    private volatile CameraCaptureSession capture;
    private volatile ImageReader reader;
    private volatile CameraOwnedPadGate gate;
    private ImageView preview;
    private TextView prompt;
    private Bitmap displayed;
    private volatile boolean running;
    private long timeout;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        timeout = Math.max(1000, Math.min(60000, getIntent().getIntExtra("CaptureTimeout",30000)));
        LinearLayout layout = new LinearLayout(this); layout.setOrientation(LinearLayout.VERTICAL);
        int padding=(int)(16*getResources().getDisplayMetrics().density);
        layout.setPadding(padding,padding,padding,padding);
        prompt=new TextView(this);prompt.setTextSize(20);prompt.setText("Preparing face check");
        preview=new ImageView(this);preview.setScaleType(ImageView.ScaleType.FIT_CENTER);
        Button cancel=new Button(this);cancel.setText("Cancel");cancel.setOnClickListener(view -> fail(FaceCaptureResult.CAPTURE_CANCELLED,"Capture cancelled"));
        layout.addView(prompt);layout.addView(preview,new LinearLayout.LayoutParams(-1,0,1));layout.addView(cancel);
        setContentView(layout);
        ui.postDelayed(() -> fail(FaceCaptureResult.CAPTURE_TIMEOUT,"Face check timed out"),timeout);
        if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{Manifest.permission.CAMERA},71);
    }
    @Override protected void onResume() {
        super.onResume();running=true;
        if(checkSelfPermission(Manifest.permission.CAMERA)==PackageManager.PERMISSION_GRANTED) start();
    }
    @Override public void onRequestPermissionsResult(int code,String[] permissions,int[] grants) {
        super.onRequestPermissionsResult(code,permissions,grants);
        if(code==71) {
            if(grants.length==1 && grants[0]==PackageManager.PERMISSION_GRANTED && running)start();
            else fail(FaceCaptureResult.CAPTURE_FAILED,"Camera permission is required");
        }
    }
    private synchronized void start() {
        if(worker!=null || finished.get())return;
        worker=new HandlerThread("PAD_CAMERA");worker.start();background=new Handler(worker.getLooper());
        background.post(() -> {
            try {
                gate=new CameraOwnedPadGate(this,timeout);
                if(!running || finished.get())return;
                CameraManager manager=(CameraManager)getSystemService(CAMERA_SERVICE);
                String selected=null;
                for(String id:manager.getCameraIdList()) {
                    if(selected==null)selected=id;
                    Integer facing=manager.getCameraCharacteristics(id).get(CameraCharacteristics.LENS_FACING);
                    if(facing!=null && facing==CameraCharacteristics.LENS_FACING_FRONT) { selected=id;break; }
                }
                if(selected==null)throw new IOException("No camera is available");
                CameraCharacteristics characteristics=manager.getCameraCharacteristics(selected);
                StreamConfigurationMap formats=characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
                Size[] choices=formats==null?null:formats.getOutputSizes(ImageFormat.JPEG);
                if(choices==null || choices.length==0)throw new IOException("Camera has no JPEG output");
                List<Size> bounded=new ArrayList<>();
                for(Size size:choices)if(size.getWidth()>=480 && size.getHeight()>=360 && size.getWidth()<=1280 && size.getHeight()<=1280)bounded.add(size);
                if(bounded.isEmpty())throw new IOException("Camera has no supported bounded JPEG size");
                Size size=Collections.min(bounded,Comparator.comparingLong(value -> (long)value.getWidth()*value.getHeight()));
                reader=ImageReader.newInstance(size.getWidth(),size.getHeight(),ImageFormat.JPEG,2);
                reader.setOnImageAvailableListener(this::imageAvailable,background);
                if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED)throw new IOException("Camera permission lost");
                manager.openCamera(selected,new CameraDevice.StateCallback() {
                    public void onOpened(CameraDevice opened) {
                        if(!running || finished.get()) { opened.close();return; }
                        camera=opened;
                        try { openSession(characteristics); }
                        catch(Exception e) { fail(FaceCaptureResult.CAPTURE_FAILED,"Camera could not start"); }
                    }
                    public void onDisconnected(CameraDevice opened) { opened.close();fail(FaceCaptureResult.CAPTURE_FAILED,"Camera disconnected"); }
                    public void onError(CameraDevice opened,int error) { opened.close();fail(FaceCaptureResult.CAPTURE_FAILED,"Camera error"); }
                },background);
            } catch(Exception | LinkageError e) { fail(FaceCaptureResult.CAPTURE_FAILED,"Face check could not start"); }
        });
    }
    private void openSession(CameraCharacteristics characteristics) throws Exception {
        camera.createCaptureSession(Collections.singletonList(reader.getSurface()),new CameraCaptureSession.StateCallback() {
            public void onConfigured(CameraCaptureSession session) {
                if(!running || finished.get()) { session.close();return; }
                capture=session;
                try {
                    CaptureRequest.Builder request=camera.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);
                    request.addTarget(reader.getSurface());
                    int rotation=getWindowManager().getDefaultDisplay().getRotation()*90;
                    Integer sensor=characteristics.get(CameraCharacteristics.SENSOR_ORIENTATION);
                    Integer facing=characteristics.get(CameraCharacteristics.LENS_FACING);
                    boolean front=facing!=null && facing==CameraCharacteristics.LENS_FACING_FRONT;
                    request.set(CaptureRequest.JPEG_ORIENTATION,((sensor==null?0:sensor)+(front?rotation:-rotation)+360)%360);
                    request.set(CaptureRequest.JPEG_QUALITY,(byte)90);
                    capture.setRepeatingRequest(request.build(),null,background);
                } catch(Exception e) { fail(FaceCaptureResult.CAPTURE_FAILED,"Camera capture unavailable"); }
            }
            public void onConfigureFailed(CameraCaptureSession session) { fail(FaceCaptureResult.CAPTURE_FAILED,"Camera configuration failed"); }
        },background);
    }
    private void imageAvailable(ImageReader source) {
        Image image=null;
        try {
            image=source.acquireLatestImage();
            if(image==null || !running || finished.get())return;
            ByteBuffer buffer=image.getPlanes()[0].getBuffer();
            if(buffer.remaining()>8*1024*1024)throw new IOException("Camera JPEG too large");
            byte[] raw=new byte[buffer.remaining()];buffer.get(raw);image.close();image=null;
            byte[] jpeg=normalize(raw);
            NativeActiveSession.State state=gate.observe(jpeg);
            if(state==NativeActiveSession.State.REJECTED) { fail(FaceCaptureResult.CAPTURE_FAILED,"Liveness could not be verified");return; }
            if(state==NativeActiveSession.State.COMPLETE) {
                if(!running || finished.get())return;
                int quality=frameQuality(jpeg);
                int threshold=Math.max(0,Math.min(100,getIntent().getIntExtra("QualityThreshold",60)));
                if(quality<threshold) { fail(FaceCaptureResult.CAPTURE_FAILED,"Image quality is too low. Try better light and keep still.");return; }
                if(!gate.consume(jpeg))throw new IOException("Completed frame binding failed");
                BitmapFactory.Options dimensions=new BitmapFactory.Options();dimensions.inJustDecodeBounds=true;
                BitmapFactory.decodeByteArray(jpeg,0,jpeg.length,dimensions);
                byte[] iso=BioFace.generateFaceISO2011(jpeg,dimensions.outHeight,dimensions.outWidth,"00");
                if(iso==null || !BioFace.isFaceISO2011Valid(iso))throw new IOException("ISO encoding failed");
                String evidence=CameraActiveEvidence.completed(iso,getIntent().getStringExtra("FacePadTransactionId"));
                ui.post(() -> {
                    if(!running || !finished.compareAndSet(false,true))return;
                    Intent result=new Intent();result.putExtra("Status",FaceCaptureResult.CAPTURE_SUCCESS);
                    result.putExtra("IsoFaceRecord",iso);result.putExtra("Quality",quality);
                    result.putExtra("FacePadEvidence",evidence);
                    setResult(Activity.RESULT_OK,result);finish();
                });
                return;
            }
            if(previewPending.compareAndSet(false,true)) {
                Bitmap next=BitmapFactory.decodeByteArray(jpeg,0,jpeg.length);
                String guidance=gate.prompt();
                ui.post(() -> {
                    try {
                        if(!running || finished.get())return;
                        displayed=next;preview.setImageBitmap(next);prompt.setText(guidance);
                    } finally { previewPending.set(false); }
                });
            }
        } catch(Exception | LinkageError e) { fail(FaceCaptureResult.CAPTURE_FAILED,"Face check failed. Restart capture."); }
        finally { if(image!=null)image.close(); }
    }
    /** Decode EXIF orientation and strip metadata before analysis and ISO encoding. */
    static byte[] normalize(byte[] bytes) throws Exception {
        android.media.ExifInterface exif=new android.media.ExifInterface(new ByteArrayInputStream(bytes));
        int orientation=exif.getAttributeInt(android.media.ExifInterface.TAG_ORIENTATION,1);
        Bitmap bitmap=BitmapFactory.decodeByteArray(bytes,0,bytes.length);
        if(bitmap==null || bitmap.getWidth()>4096 || bitmap.getHeight()>4096)throw new IOException("Invalid camera image");
        Matrix transform=new Matrix();
        switch(orientation) {
            case 2:transform.setScale(-1,1);break;
            case 3:transform.setRotate(180);break;
            case 4:transform.setScale(1,-1);break;
            case 5:transform.setRotate(90);transform.postScale(-1,1);break;
            case 6:transform.setRotate(90);break;
            case 7:transform.setRotate(270);transform.postScale(-1,1);break;
            case 8:transform.setRotate(270);break;
            default:break;
        }
        Bitmap upright=Bitmap.createBitmap(bitmap,0,0,bitmap.getWidth(),bitmap.getHeight(),transform,true);
        try(ByteArrayOutputStream output=new ByteArrayOutputStream()) {
            if(!upright.compress(Bitmap.CompressFormat.JPEG,90,output))throw new IOException("JPEG encoding failed");
            return output.toByteArray();
        } finally { if(upright!=bitmap)upright.recycle();bitmap.recycle(); }
    }
    /** Uncalibrated research image-quality score, separate from PAD confidence. */
    static int frameQuality(byte[] jpeg) throws Exception {
        MatOfByte bytes=new MatOfByte(jpeg);Mat image=null,gray=new Mat(),edges=new Mat();
        MatOfDouble mean=new MatOfDouble(),deviation=new MatOfDouble();
        try {
            image=Imgcodecs.imdecode(bytes,Imgcodecs.IMREAD_COLOR);
            if(image.empty())throw new IOException("Invalid quality image");
            Imgproc.cvtColor(image,gray,Imgproc.COLOR_BGR2GRAY);Imgproc.Laplacian(gray,edges,CvType.CV_64F);
            Core.meanStdDev(edges,mean,deviation);
            double variance=Math.pow(deviation.toArray()[0],2);
            double exposure=Math.max(0,1-Math.abs(Core.mean(gray).val[0]-128)/100.0);
            return (int)Math.round(100*Math.min(exposure,Math.min(1,variance/150.0)));
        } finally { bytes.release();if(image!=null)image.release();gray.release();edges.release();mean.release();deviation.release(); }
    }
    private void fail(int status,String message) {
        ui.post(() -> {
            if(!finished.compareAndSet(false,true))return;
            Intent result=new Intent();result.putExtra("Status",status);result.putExtra("msg",message);
            result.putExtra("IsoFaceRecord",new byte[0]);result.putExtra("Quality",0);
            setResult(Activity.RESULT_CANCELED,result);finish();
        });
    }
    @Override protected void onPause() {
        running=false;
        if(capture!=null) { capture.close();capture=null; }
        if(camera!=null) { camera.close();camera=null; }
        if(reader!=null) { reader.close();reader=null; }
        if(background!=null)background.post(() -> {try {if(gate!=null)gate.close();}catch(Exception ignored){} });
        if(worker!=null)worker.quitSafely();
        if(!finished.get() && worker!=null)fail(FaceCaptureResult.CAPTURE_CANCELLED,"Capture interrupted");
        super.onPause();
    }
    @Override protected void onDestroy() {
        ui.removeCallbacksAndMessages(null);
        if(displayed!=null) { preview.setImageDrawable(null);displayed=null; }
        super.onDestroy();
    }
    @Override public void onBackPressed() { fail(FaceCaptureResult.CAPTURE_CANCELLED,"Capture cancelled"); }
}
