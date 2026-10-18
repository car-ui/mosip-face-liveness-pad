import io.mosip.registration.liveness.NativeCaptureGate;
import io.mosip.registration.liveness.MosipLivenessDeviceService;

/** No JUnit dependency. Throws on failure, including when Java assertions are disabled. */
public class NativeCaptureGateTest {
    private static int checks = 0;
    private static void check(boolean condition) {
        checks++;
        if (!condition) throw new AssertionError("Failed check " + checks);
    }
    public static void main(String[] args) throws Exception {
        byte[] jpeg = new byte[]{1, 2, 3};
        NativeCaptureGate gate = new NativeCaptureGate(2, 30000);
        String id = gate.sessionId();
        check(!gate.observe(id, 1, true, true, false, true, null, jpeg));
        check(!gate.observe(id, 2, true, true, false, true, "nonce-1", jpeg));
        check(!gate.observe(id, 3, true, true, false, true, "nonce-1", jpeg));
        check(gate.observe(id, 4, true, true, false, false, "nonce-2", jpeg));
        check(gate.consume(id, jpeg));
        check(!gate.consume(id, jpeg));
        for (int scenario = 0; scenario < 5; scenario++) {
            gate = new NativeCaptureGate(1, 30000); id = gate.sessionId();
            check(!gate.observe(scenario == 0 ? "wrong-session" : id, 1, scenario != 1,
                    scenario != 2, scenario == 3, true, null, jpeg));
            if (scenario == 4) {
                check(!gate.observe(id, 1, true, true, false, true, "nonce", jpeg));
            }
            check(!gate.consume(id, jpeg));
        }
        gate = new NativeCaptureGate(0, 30000); id = gate.sessionId();
        check(gate.observe(id, 1, true, true, false, true, null, jpeg));
        check(!gate.consume(id, new byte[]{4, 5}));
        try { new MosipLivenessDeviceService("http://example.com", "test"); throw new AssertionError(); }
        catch (IllegalArgumentException expected) { checks++; }
        System.out.println(checks + " native policy/transport checks passed; inference and native client integration are not tested.");
    }
}
