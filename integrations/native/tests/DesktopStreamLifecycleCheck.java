import io.mosip.registration.controller.device.Streamer;
import java.awt.image.BufferedImage;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import javafx.application.Platform;
import javafx.scene.image.ImageView;
import javax.imageio.ImageIO;

/** Actual upstream preview/session lifecycle with controlled streams, no camera. */
public final class DesktopStreamLifecycleCheck {
    private static final class BlockingCamera extends InputStream {
        private final byte[] prefix;
        private final boolean delayDisconnect;
        private int offset;
        private final CountDownLatch reading = new CountDownLatch(1);
        private final CountDownLatch release = new CountDownLatch(1);
        private volatile boolean closed;
        private volatile Thread readerThread;
        BlockingCamera(byte[] prefix, boolean delayDisconnect) {
            this.prefix = prefix; this.delayDisconnect = delayDisconnect;
        }
        public int read() throws IOException {
            readerThread = Thread.currentThread();
            if (offset < prefix.length) return prefix[offset++] & 255;
            reading.countDown();
            try {
                if (!release.await(5, TimeUnit.SECONDS)) throw new IOException("Test stream deadline");
            } catch (InterruptedException e) { Thread.currentThread().interrupt(); throw new IOException(e); }
            throw new EOFException("Controlled camera disconnect");
        }
        public int read(byte[] b, int off, int len) throws IOException {
            if (offset >= prefix.length) return read();
            int count = Math.min(len, prefix.length - offset);
            System.arraycopy(prefix, offset, b, off, count); offset += count; return count;
        }
        public void close() { closed = true; if (!delayDisconnect) release.countDown(); }
    }

    private static void fx(Runnable action) throws Exception {
        FutureTask<Void> task = new FutureTask<>(action, null);
        Platform.runLater(task); task.get(3, TimeUnit.SECONDS);
    }

    public static void main(String[] args) throws Exception {
        CountDownLatch started = new CountDownLatch(1);
        Platform.startup(started::countDown);
        if (!started.await(3, TimeUnit.SECONDS)) throw new AssertionError("JavaFX startup timeout");
        Streamer stream = new Streamer();
        BlockingCamera old = new BlockingCamera(new byte[0], true);
        BlockingCamera replacement = null;
        try {
            AtomicReference<ImageView> preview = new AtomicReference<>();
            AtomicBoolean wrongThread = new AtomicBoolean();
            CountDownLatch displayed = new CountDownLatch(1);
            fx(() -> {
                ImageView view = new ImageView();
                view.imageProperty().addListener((property, before, after) -> {
                    if (!Platform.isFxApplicationThread()) wrongThread.set(true);
                    if (after != null) displayed.countDown();
                });
                preview.set(view);
            });
            stream.startStream(old, preview.get(), preview.get());
            if (!old.reading.await(2, TimeUnit.SECONDS)) throw new AssertionError("Old camera did not start");
            ByteArrayOutputStream jpeg = new ByteArrayOutputStream();
            ImageIO.write(new BufferedImage(160, 120, BufferedImage.TYPE_3BYTE_BGR), "jpg", jpeg);
            ByteArrayOutputStream part = new ByteArrayOutputStream();
            part.write(("--camera\r\nContent-Type: image/jpeg\r\nContent-Length: " + jpeg.size() + "\r\n\r\n")
                    .getBytes(StandardCharsets.US_ASCII));
            part.write(jpeg.toByteArray());
            replacement = new BlockingCamera(part.toByteArray(), false);
            stream.startStream(replacement, preview.get(), preview.get());
            if (!old.closed) throw new AssertionError("Replacement did not close previous camera");
            if (!replacement.reading.await(2, TimeUnit.SECONDS) || !displayed.await(2, TimeUnit.SECONDS))
                throw new AssertionError("Replacement preview did not progress");
            // The old reader exits after the new stream has published its frame.
            old.release.countDown();
            old.readerThread.join(2000);
            if (old.readerThread.isAlive()) throw new AssertionError("Old camera reader did not terminate");
            fx(() -> { });
            if (stream.getUrlStream() != replacement || replacement.closed)
                throw new AssertionError("Old camera closed replacement");
            byte[] cached = stream.getStreamImageBytes();
            if (!java.util.Arrays.equals(cached, jpeg.toByteArray())) throw new AssertionError("Frame bytes changed");
            cached[0] = 0;
            if (stream.getStreamImageBytes()[0] == 0) throw new AssertionError("Mutable frame cache exposed");
            if (wrongThread.get()) throw new AssertionError("Preview updated outside JavaFX thread");
            System.out.println("PASS actual Streamer preview on JavaFX thread and exact JPEG cache with defensive copy");
            System.out.println("PASS camera replacement survives delayed EOF from the previous reader");
            stream.stop();
            if (!replacement.closed || stream.getUrlStream() != null || stream.getStreamImageBytes() != null
                    || stream.getStreamImage() != null) throw new AssertionError("Stop retained camera state");
            System.out.println("PASS stop closes camera and clears cached image/bytes");
            System.out.println("Evidence scope: actual upstream Streamer and JavaFX ImageView; synthetic JPEG, no physical camera or full client UI");
        } finally {
            old.release.countDown();
            stream.stop();
            if (replacement != null) replacement.release.countDown();
            Platform.exit();
        }
    }
}
