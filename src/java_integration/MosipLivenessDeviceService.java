package io.mosip.registration.liveness;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/** Java 8+ transport example for the custom research API, not a MOSIP SBI SDK. */
public final class MosipLivenessDeviceService {
    private final URI base;
    private final String token;

    public MosipLivenessDeviceService(String baseUrl, String token) {
        this.base = URI.create(baseUrl == null ? "http://127.0.0.1:4501" : baseUrl);
        if (!"http".equals(base.getScheme()) ||
            !("127.0.0.1".equals(base.getHost()) || "localhost".equals(base.getHost())) ||
            base.getUserInfo() != null || base.getQuery() != null || base.getFragment() != null) {
            throw new IllegalArgumentException("Use a loopback HTTP service URL");
        }
        this.token = token;
    }

    public MosipLivenessDeviceService(String baseUrl) {
        this(baseUrl, System.getenv("MOSIP_MDS_API_TOKEN"));
    }

    private String request(String endpoint, String body, int timeoutMillis) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) base.resolve(endpoint).toURL().openConnection();
        connection.setConnectTimeout(3000);
        connection.setReadTimeout(timeoutMillis);
        connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("Accept", "application/json");
        try {
            if (body != null) {
                if (token == null || token.isEmpty()) throw new IllegalStateException("Set MOSIP_MDS_API_TOKEN");
                connection.setRequestMethod("POST");
                connection.setRequestProperty("Authorization", "Bearer " + token);
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setDoOutput(true);
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(body.getBytes(StandardCharsets.UTF_8));
                }
            }
            int status = connection.getResponseCode();
            if (status != 200) throw new IllegalStateException("Capture service returned HTTP " + status);
            try (InputStream input = connection.getInputStream(); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] block = new byte[8192];
                int count;
                while ((count = input.read(block)) != -1) {
                    if (output.size() + count > 8 * 1024 * 1024) throw new IllegalStateException("Response too large");
                    output.write(block, 0, count);
                }
                return new String(output.toByteArray(), StandardCharsets.UTF_8);
            }
        } finally {
            connection.disconnect();
        }
    }

    public String getDeviceInfo() throws Exception { return request("/info", null, 3000); }

    /** The caller must parse the response and apply a capture gate before accepting bytes. */
    public String captureBiometric(String workflow, int timeoutSeconds) throws Exception {
        if (!Arrays.asList("RESIDENT_REGISTRATION", "OPERATOR_AUTHENTICATION", "SUPERVISOR_AUTHENTICATION").contains(workflow))
            throw new IllegalArgumentException("Unknown workflow");
        if (timeoutSeconds < 2 || timeoutSeconds > 60) throw new IllegalArgumentException("Timeout must be 2..60 seconds");
        String body = String.format("{\"workflow\":\"%s\",\"timeout_seconds\":%d}", workflow, timeoutSeconds);
        return request("/capture", body, (timeoutSeconds + 5) * 1000);
    }

    public static void main(String[] args) throws Exception {
        MosipLivenessDeviceService client = new MosipLivenessDeviceService(null);
        client.getDeviceInfo();
        System.out.println("Local research service discovery succeeded. No biometric capture was requested.");
    }
}
