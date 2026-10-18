package io.mosip.facepad;

import io.mosip.biometrics.util.ConvertRequestDto;
import io.mosip.biometrics.util.face.FaceDecoder;
import io.mosip.registration.dto.packetmanager.BiometricsDto;
import java.io.*;
import java.nio.file.*;
import java.util.List;

/** Called before registration storage and before operator face matching. */
public final class DesktopPadCheckpoint {
    private static NativePadEngine engine;
    private DesktopPadCheckpoint() { }

    private static synchronized NativePadEngine engine() throws Exception {
        if (engine == null) {
            nu.pattern.OpenCV.loadLocally();
            Path cascade = Files.createTempFile("facepad-cascade-", ".xml");
            try (InputStream stream = resource("haarcascade_frontalface_default.xml")) {
                Files.copy(stream, cascade, StandardCopyOption.REPLACE_EXISTING);
            }
            try (InputStream stream = resource("minifasnet_v2.onnx")) {
                engine = new NativePadEngine(read(stream), cascade);
            } finally { Files.deleteIfExists(cascade); }
        }
        return engine;
    }

    private static InputStream resource(String name) throws IOException {
        InputStream stream = DesktopPadCheckpoint.class.getResourceAsStream("/facepad/" + name);
        if (stream == null) throw new IOException("PAD resource missing: " + name);
        return stream;
    }

    private static byte[] read(InputStream stream) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192]; int count;
        while ((count = stream.read(buffer)) != -1) out.write(buffer, 0, count);
        return out.toByteArray();
    }

    public static void requireClear(List<BiometricsDto> biometrics, boolean activeRequired) throws IOException {
        if (biometrics == null || biometrics.size() != 1) throw new IOException("PAD: expected one face capture");
        try {
            ConvertRequestDto request = new ConvertRequestDto();
            request.setVersion("ISO19794_5_2011");
            request.setInputBytes(biometrics.get(0).getAttributeISO());
            NativePadEngine.Decision decision = engine().evaluateEncoded(FaceDecoder.convertFaceISOToImageBytes(request), activeRequired);
            if (!decision.accepted) throw new IOException("PAD rejected face capture: " + decision.reason);
        } catch (IOException e) { throw e; }
        catch (Exception | LinkageError e) { throw new IOException("PAD unavailable; face capture rejected", e); }
    }
}
