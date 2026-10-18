import io.mosip.facepad.BoundedMjpegReader;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/** Framing tests use marker bytes, not a decoded photograph or a PAD result. */
public final class BoundedMjpegReaderCheck {
    private static int checks;
    private static final byte[] JPEG = {(byte)255, (byte)216, 1, 2, (byte)255, (byte)217};
    private static byte[] part(String headers, byte[] data) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        out.write(headers.getBytes(StandardCharsets.US_ASCII)); out.write(data); return out.toByteArray();
    }
    private static void rejects(byte[] bytes) throws IOException {
        try { BoundedMjpegReader.readFrame(new ByteArrayInputStream(bytes)); }
        catch (IOException expected) { checks++; return; }
        throw new AssertionError("Malformed stream accepted");
    }
    public static void main(String[] args) throws Exception {
        byte[] first = part("--camera\r\nContent-Type: image/jpeg\r\nContent-Length: 6\r\n\r\n", JPEG);
        byte[] second = part("\r\n--camera\r\ncontent-length: 6\r\n\r\n", JPEG);
        ByteArrayOutputStream both = new ByteArrayOutputStream(); both.write(first); both.write(second);
        InputStream fragmented = new FilterInputStream(new ByteArrayInputStream(both.toByteArray())) {
            public int read(byte[] b, int off, int len) throws IOException { return super.read(b, off, Math.min(len, 1)); }
        };
        for (int i = 0; i < 2; i++) {
            if (!Arrays.equals(JPEG, BoundedMjpegReader.readFrame(fragmented))) throw new AssertionError("Frame changed");
            checks++;
        }
        rejects(new byte[0]);
        rejects(part("Content-Length: 6\r\n\r\n", Arrays.copyOf(JPEG, 4)));
        rejects(part("Content-Length: -1\r\n\r\n", JPEG));
        rejects(part("Content-Length: 99999999\r\n\r\n", JPEG));
        rejects(part("Content-Length: 6\r\nContent-Length: 6\r\n\r\n", JPEG));
        rejects(part("Content-Type: image/jpeg\r\n\r\n", JPEG));
        rejects(part("Content-Type: text/plain\r\nContent-Length: 6\r\n\r\n", JPEG));
        rejects(part("Content-Length: 6\r\n\r\n", new byte[6]));
        rejects("--camera--\r\n".getBytes(StandardCharsets.US_ASCII));
        rejects(new byte[BoundedMjpegReader.MAX_HEADER_BYTES + 1]);
        rejects(part("Content-Length: 6\r\n--camera\r\n\r\n", JPEG));
        InputStream zeroRead = new FilterInputStream(new ByteArrayInputStream(first)) {
            public int read(byte[] b, int off, int len) { return 0; }
        };
        if (!Arrays.equals(JPEG, BoundedMjpegReader.readFrame(zeroRead))) throw new AssertionError("Zero-read recovery failed");
        checks++;
        System.out.println("PASS " + checks + " camera framing checks: consecutive/fragmented parts, EOF, truncation, bounds, headers and JPEG markers");
    }
}
