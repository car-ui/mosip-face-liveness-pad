# Local research API

Run `python run_mds_service.py`. The service listens at `http://127.0.0.1:4501`. This is a custom research API, not the MOSIP SBI wire protocol. Browse `/docs` for generated request schemas and `/openapi.json` for machine-readable documentation.

## Authentication

All POST endpoints require `Authorization: Bearer <local-token>`. The same-origin console receives a process-generated token. To use another local client, set a strong `MOSIP_MDS_API_TOKEN` environment variable in both the server and client processes before starting them. Do not include tokens in source, screenshots, URLs, or submission documents. GET endpoints are local diagnostic/preview endpoints without authentication; any process on the same machine can access them. The threat model excludes a compromised local user account.

Browser mutations also require an allowed origin when the `Origin` header is present. Only the service's localhost origins are accepted. Hostname checks block DNS-rebinding hostnames. Cross-origin access controls do not provide authentication for local non-browser processes.

## Endpoints

| Method and path | Purpose | Response |
|---|---|---|
| `GET /` | Same-origin evaluator console | HTML, ephemeral token, no-store |
| `GET /info` | Device and model capabilities | Device ID, status, security level, simulation flag, engine mode, `NOT_CERTIFIED` |
| `GET /stream` | MJPEG positioning preview | Multipart JPEG; never advances pipeline decisions |
| `GET /status` | Current guidance and progress | State, prompt, progress, retry counters; no images |
| `GET /configuration` | Current nonsecret policy settings | Global settings and all workflow profiles |
| `GET /metrics` | Anonymous counters for this process | Session counts, outcomes, mean capture/challenge duration, retry/failure rate |
| `POST /capture` | Start exclusive verification session | Success with application JPEG, or empty biometrics on failure |
| `POST /configure` | Validate and apply policy changes | Applied policy and actual engine mode |
| `POST /switch-device` | Explicitly choose webcam or simulator | Selected device ID or HTTP 503 if unavailable |

## Capture request

```json
{"workflow":"OPERATOR_AUTHENTICATION","timeout_seconds":30}
```

Workflows are `RESIDENT_REGISTRATION`, `OPERATOR_AUTHENTICATION`, and `SUPERVISOR_AUTHENTICATION`. `timeout_seconds` is an integer from 2 to 60. An optional `resident_id` is returned to the requesting client and is not an authentication identity or a log field.

Success returns `responseStatus: SUCCESS`, `decision: PASSED`, `simulation`, `identityMatchPerformed: false`, and one `biometrics` item containing `specVersion: APPLICATION_JPEG`, Base64 `data`, `mimeType: image/jpeg`, `tokenHash`, `livenessVerified`, and the actual passive confidence. `tokenHash` is SHA-256 over the decoded JPEG bytes. It is an integrity digest, not a digital signature or a face template. Telemetry contains actual workflow, duration, completed actions, mode, and model provenance. Success in simulation remains explicitly simulated.

Failure returns `biometrics: []` and a safe explanation. The caller must inspect `responseStatus` and `decision`. HTTP 200 alone never means liveness passed. Verification expiry returns HTTP 200 with `responseStatus: TIMEOUT`, because the request completed and the verification failed. HTTP 408 is deliberately avoided because Chromium can transparently retry it and restart capture. HTTP 503 indicates an unavailable/disconnected device; HTTP 409 indicates another capture owns the device; HTTP 401/403 indicates authentication/origin rejection; HTTP 422 indicates invalid input.

## Configuration example

```json
{
  "workflow":"SUPERVISOR_AUTHENTICATION",
  "passive_threshold":0.94,
  "min_challenges":2,
  "challenge_timeout":8,
  "max_retries":2,
  "active_liveness_enabled":true,
  "require_active_challenges":true,
  "supported_challenges":["BLINK","TURN_LEFT","TURN_RIGHT"],
  "pad_mode":"ONNX",
  "guidance_messages":{"FACE_DETECTION":"Keep one face inside the guide."}
}
```

`pad_mode` accepts `AUTO`, `HEURISTIC`, or `ONNX`. Strict ONNX mode rejects a missing or failing model. Global `liveness_enabled: false` prevents verified capture rather than labeling an unchecked image as verified. Required active challenges cannot coexist with active verification disabled. Guidance keys must be pipeline state names and values are limited to 300 characters. Unknown fields, devices, scenarios, and modes are rejected, not silently replaced with a live simulator. Configuration is in memory and resets on service restart.

## Device selection example

```json
{"device_mode":"MOCK","scenario":"SCREEN_REPLAY_ATTACK"}
```

`device_mode` accepts `MOCK`, `WEBCAM`, or `L1`. `L1` is a simulated vendor adapter and has no secure hardware or attestation. Use `GET /info` to inspect the actual source after changing it.

The Java transport example intentionally does not parse a result into a trusted authentication decision. An integrating client needs a JSON parser, response validation, session/payload binding, trusted model results, and its normal identity matching control.
