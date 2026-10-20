package io.mosip.facepad;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import com.gemalto.jp2.JP2Decoder;
import io.mosip.biometrics.util.face.FaceBDIR;
import io.mosip.registration.clientmanager.dto.registration.BiometricsDto;
import java.io.*;
import java.util.List;
import org.opencv.android.OpenCVLoader;
import org.opencv.android.Utils;
import org.opencv.core.Mat;
import org.opencv.imgproc.Imgproc;

/** Offline checkpoint for the exact SBI result, before any registration/onboarding storage. */
public final class AndroidPadCheckpoint {
    private static NativePadEngine engine;
    private AndroidPadCheckpoint() { }

    private static synchronized NativePadEngine engine(Context context) throws Exception {
        if (engine == null) {
            if (!OpenCVLoader.initLocal()) throw new IOException("OpenCV unavailable");
            try (InputStream input = context.getAssets().open("facepad/minifasnet_v2.onnx");
                 InputStream faceInput = context.getAssets().open("facepad/face_detection_yunet_2023mar.onnx");
                 ByteArrayOutputStream output = new ByteArrayOutputStream();
                 ByteArrayOutputStream faceOutput = new ByteArrayOutputStream()) {
                copy(input, output);
                copy(faceInput,faceOutput);
                engine = new NativePadEngine(output.toByteArray(), faceOutput.toByteArray());
            }
        }
        return engine;
    }

    private static void copy(InputStream input, OutputStream output) throws IOException {
        byte[] buffer = new byte[8192]; int count;
        while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
    }

    public static void requireClear(Context context, List<BiometricsDto> biometrics, boolean activeRequired) throws IOException {
        requireClear(context,biometrics,activeRequired,null);
    }

    public static void requireClear(Context context, List<BiometricsDto> biometrics, boolean activeRequired,
                                    String transactionId) throws IOException {
        requireClear(context,biometrics,NativePadPolicy.defaults(activeRequired ? NativePadPolicy.Workflow.OPERATOR : NativePadPolicy.Workflow.RESIDENT),transactionId);
    }

    public static void requireClear(Context context, List<BiometricsDto> biometrics, NativePadPolicy policy,
                                    String transactionId) throws IOException {
        if (biometrics == null || biometrics.size() != 1) throw new IOException("PAD: expected one face capture");
        if (policy == null || !policy.enabled) throw new IOException("PAD: liveness disabled; capture is unverified");
        Bitmap bitmap = null;
        Mat rgba = null, bgr = null;
        try {
            NativePadEngine evaluator = engine(context);
            rgba = new Mat(); bgr = new Mat();
            // SBI signature and transaction validation run upstream before this method.
            byte[] iso = java.util.Base64.getUrlDecoder().decode(biometrics.get(0).getBioValue());
            if(iso.length>8*1024*1024)throw new IOException("PAD: ISO capture too large");
            byte[] encoded = new FaceBDIR(new DataInputStream(new ByteArrayInputStream(iso)))
                    .getRepresentation().getRepresentationData().getImageData().getImage();
            BoundedImage.requireImage(encoded);
            BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;
            BitmapFactory.decodeByteArray(encoded,0,encoded.length,bounds);
            if(bounds.outWidth>4096 || bounds.outHeight>4096)throw new IOException("PAD: image dimensions too large");
            bitmap = BitmapFactory.decodeByteArray(encoded, 0, encoded.length);
            if (bitmap == null) bitmap = new JP2Decoder(encoded).decode();
            if (bitmap == null) throw new IOException("PAD: image decoding failed");
            Utils.bitmapToMat(bitmap, rgba);
            Imgproc.cvtColor(rgba, bgr, Imgproc.COLOR_RGBA2BGR);
            NativePadEngine.Decision decision = evaluator.evaluateBgr(bgr, policy);
            if (!decision.accepted) {
                if(!"ACTIVE_CHALLENGE_REQUIRED".equals(decision.reason))
                    throw new IOException("PAD rejected face capture: " + decision.reason);
                AndroidActiveEvidence.verifyAndConsume(context,biometrics.get(0),iso,transactionId,policy);
            }
        } catch (IOException e) { throw e; }
        catch (Exception | LinkageError e) { throw new IOException("PAD unavailable; face capture rejected", e); }
        finally { if (bitmap != null) bitmap.recycle(); if (rgba != null) rgba.release(); if (bgr != null) bgr.release(); }
    }
}
