package io.mosip.registration.liveness;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * MOSIP Desktop Registration Client - Face Liveness Device Service Adapter
 * 
 * Demonstrates integration into the existing MOSIP Java Registration Client:
 * 1. Device discovery handshake via /info
 * 2. Biometric capture trigger via /capture
 * 3. Processing ISO/IEC 19794-5-aligned facial image representation and ISO/IEC 30107 PAD verification response
 */
public class MosipLivenessDeviceService {

    private final String mdsBaseUrl;

    public MosipLivenessDeviceService(String mdsBaseUrl) {
        this.mdsBaseUrl = mdsBaseUrl != null ? mdsBaseUrl : "http://127.0.0.1:4501";
    }

    /**
     * Checks if the MOSIP L0/L1 Device Service is running and reports capability.
     */
    public String getDeviceInfo() throws Exception {
        URL url = URI.create(mdsBaseUrl + "/info").toURL();
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setRequestProperty("Accept", "application/json");

        if (conn.getResponseCode() != 200) {
            throw new RuntimeException("MDS Device discovery failed with HTTP code: " + conn.getResponseCode());
        }

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
            StringBuilder response = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                response.append(line);
            }
            return response.toString();
        }
    }

    /**
     * Initiates biometric capture with liveness verification for a specific workflow.
     * 
     * @param workflow "RESIDENT_REGISTRATION", "OPERATOR_AUTHENTICATION", or "SUPERVISOR_AUTHENTICATION"
     * @param timeoutSeconds Session timeout in seconds
     * @return JSON response containing ISO/IEC 19794-5-aligned image payload and PAD verification token
     */
    public String captureBiometric(String workflow, int timeoutSeconds) throws Exception {
        URL url = URI.create(mdsBaseUrl + "/capture").toURL();
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setRequestProperty("Accept", "application/json");
        conn.setDoOutput(true);

        String jsonPayload = String.format("{\"workflow\":\"%s\",\"timeout_seconds\":%d}", workflow, timeoutSeconds);

        try (OutputStream os = conn.getOutputStream()) {
            byte[] input = jsonPayload.getBytes(StandardCharsets.UTF_8);
            os.write(input, 0, input.length);
        }

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
            StringBuilder response = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                response.append(line);
            }
            return response.toString();
        }
    }

    public static void main(String[] args) {
        System.out.println("Starting MOSIP Desktop Client - Liveness Adapter...");
        MosipLivenessDeviceService client = new MosipLivenessDeviceService("http://127.0.0.1:4501");
        try {
            System.out.println("Connecting to MOSIP Device Service...");
            String info = client.getDeviceInfo();
            System.out.println("Device Info Received: " + info);

            System.out.println("\nTriggering Resident Registration Face Capture...");
            String result = client.captureBiometric("RESIDENT_REGISTRATION", 15);
            System.out.println("Capture Result: " + result);
        } catch (Exception e) {
            System.err.println("Could not connect to MDS: " + e.getMessage());
            System.err.println("Ensure the Python MDS server (run_mds_service.py) is running on port 4501.");
        }
    }
}
