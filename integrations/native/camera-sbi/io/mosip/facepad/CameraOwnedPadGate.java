package io.mosip.facepad;

import android.content.Context;
import java.io.*;
import org.opencv.android.OpenCVLoader;

/** In-process camera-owner gate. No caller-supplied success flag or score is accepted. */
public final class CameraOwnedPadGate implements AutoCloseable {
    private final NativePadEngine pad;
    private final NativeLandmarkEngine landmarks;
    private final NativeFrameChallenge active;
    private boolean closed;

    public CameraOwnedPadGate(Context context, long timeoutMillis) throws Exception {
        this(context, timeoutMillis, NativePadPolicy.defaults(NativePadPolicy.Workflow.OPERATOR));
    }

    public CameraOwnedPadGate(Context context, long timeoutMillis, NativePadPolicy policy) throws Exception {
        if (!OpenCVLoader.initLocal()) throw new IOException("OpenCV unavailable");
        if (policy == null || !policy.enabled || !policy.activeEnabled || !policy.activeRequired)
            throw new IOException("Mandatory camera PAD policy unavailable");
        NativePadEngine loadedPad = null;
        NativeLandmarkEngine loadedLandmarks = null;
        try {
            loadedPad = new NativePadEngine(asset(context,"minifasnet_v2.onnx"),asset(context,"face_detection_yunet_2023mar.onnx"));
            loadedLandmarks = new NativeLandmarkEngine(asset(context,"facemesh_v2.onnx"));
            active = new NativeFrameChallenge(loadedPad,loadedLandmarks,timeoutMillis,policy);
            pad = loadedPad; landmarks = loadedLandmarks;
        } catch (Exception | LinkageError failure) {
            if (loadedLandmarks != null) loadedLandmarks.close();
            if (loadedPad != null) loadedPad.close();
            throw failure;
        }
    }

    private static byte[] asset(Context context,String name) throws IOException {
        try (InputStream input=context.getAssets().open("facepad/"+name);
             ByteArrayOutputStream output=new ByteArrayOutputStream()) {
            transfer(input,output);return output.toByteArray();
        }
    }
    private static void transfer(InputStream input,OutputStream output) throws IOException {
        byte[] buffer=new byte[8192];int count;
        while((count=input.read(buffer))!=-1)output.write(buffer,0,count);
    }
    public synchronized NativeActiveSession.State observe(byte[] exactCameraJpeg) throws Exception {
        if(closed)throw new IOException("Camera session closed");
        return active.observe(exactCameraJpeg);
    }
    public synchronized String prompt() { return closed?"Camera stopped":active.prompt(); }
    public synchronized boolean consume(byte[] exactCameraJpeg) throws Exception {
        return !closed && active.consume(exactCameraJpeg);
    }
    public synchronized NativeActiveSession.Attestation consumeAndAttest(byte[] exactCameraJpeg) throws Exception {
        return closed ? null : active.consumeAndAttest(exactCameraJpeg);
    }
    @Override public synchronized void close() throws Exception {
        if(closed)return;
        closed=true;active.cancel();
        try { landmarks.close(); } finally { pad.close(); }
    }
}
