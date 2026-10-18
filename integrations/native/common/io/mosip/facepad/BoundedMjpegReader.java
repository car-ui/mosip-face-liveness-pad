package io.mosip.facepad;

import java.io.ByteArrayOutputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/** Reads one length-delimited JPEG part without consuming the following part. */
public final class BoundedMjpegReader {
    public static final int MAX_HEADER_BYTES = 16 * 1024;
    public static final int MAX_FRAME_BYTES = 8 * 1024 * 1024;
    private BoundedMjpegReader() { }

    public static byte[] readFrame(InputStream input) throws IOException {
        if (input == null) throw new IOException("Camera stream unavailable");
        int remaining = MAX_HEADER_BYTES;
        int length = -1;
        boolean started = false;
        while (true) {
            ByteArrayOutputStream line = new ByteArrayOutputStream();
            int value;
            while (true) {
                if (--remaining < 0) throw new IOException("Camera part headers too large");
                value = input.read();
                if (value == -1) throw new EOFException("Camera stream ended in headers");
                if (value == '\n') break;
                if (value != '\r') line.write(value);
            }
            String header = new String(line.toByteArray(), StandardCharsets.US_ASCII).trim();
            if (header.isEmpty()) {
                if (started) break;
                continue;
            }
            if (header.startsWith("--")) {
                if (header.endsWith("--")) throw new EOFException("Camera multipart stream ended");
                if (started) throw new IOException("Unexpected boundary within camera headers");
                continue;
            }
            started = true;
            int colon = header.indexOf(':');
            if (colon <= 0) throw new IOException("Malformed camera part header");
            String name = header.substring(0, colon).trim();
            String content = header.substring(colon + 1).trim();
            if (name.equalsIgnoreCase("Content-Length")) {
                if (length != -1) throw new IOException("Duplicate camera content length");
                if (!content.matches("[0-9]{1,8}")) throw new IOException("Invalid camera content length");
                length = Integer.parseInt(content);
                if (length < 4 || length > MAX_FRAME_BYTES) throw new IOException("Camera frame size outside bounds");
            } else if (name.equalsIgnoreCase("Content-Type") && !content.equalsIgnoreCase("image/jpeg")) {
                throw new IOException("Camera part is not JPEG");
            }
        }
        if (length == -1) throw new IOException("Camera part has no content length");
        byte[] frame = new byte[length];
        int offset = 0;
        while (offset < length) {
            int count = input.read(frame, offset, length - offset);
            if (count < 0) throw new EOFException("Camera JPEG truncated");
            if (count == 0) {
                int value = input.read();
                if (value < 0) throw new EOFException("Camera JPEG truncated");
                frame[offset++] = (byte) value;
            } else offset += count;
        }
        if ((frame[0] & 255) != 255 || (frame[1] & 255) != 216
                || (frame[length - 2] & 255) != 255 || (frame[length - 1] & 255) != 217)
            throw new IOException("Camera JPEG markers invalid");
        return frame;
    }
}
