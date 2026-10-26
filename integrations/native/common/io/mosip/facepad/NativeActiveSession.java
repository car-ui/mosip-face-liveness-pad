package io.mosip.facepad;

import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Set;
import java.util.function.LongSupplier;

/** Session-bound action progression for trusted frame adapters and exact-image consumers. */
public final class NativeActiveSession {
    public enum State { VERIFYING, COMPLETE, REJECTED, CONSUMED }
    private enum Action { BLINK, TURN_IMAGE_LEFT, TURN_IMAGE_RIGHT }
    private final LongSupplier clock;
    private final long startedAt, timeoutNanos;
    private final long startedAtMillis;
    private final long timeoutMillis;
    private final Action[] actions;
    private final int maxRetries;
    private int retries;
    private State state = State.VERIFYING;
    private int action, phase, stable;
    private long lastSequence = -1, lastTime = -1, heldSince;
    private boolean observed;
    private long completedAt;
    private long completedAtMillis;
    private long actionPromptAt;
    private byte[] candidateDigest;
    private int padStreak;
    private boolean padClear;
    private Long padStarted, padLast;
    private long padHeldSince;

    public NativeActiveSession(long timeoutMillis) {
        this(timeoutMillis, System::nanoTime, new SecureRandom());
    }

    // Package-private deterministic clock/randomness is used only by control-flow tests.
    NativeActiveSession(long timeoutMillis, LongSupplier clock, SecureRandom random) {
        this(timeoutMillis, 2, 2, clock, random);
    }

    public NativeActiveSession(NativePadPolicy policy) {
        this(policy.timeoutSeconds * 1000L, policy);
    }

    public NativeActiveSession(long timeoutMillis, NativePadPolicy policy) {
        this(Math.min(timeoutMillis, policy.timeoutSeconds * 1000L), policy.actionCount, policy.maxRetries,
                policy.challengeTypes, System::nanoTime, new SecureRandom());
    }

    NativeActiveSession(long timeoutMillis, int actionCount, int maxRetries, LongSupplier clock, SecureRandom random) {
        this(timeoutMillis, actionCount, maxRetries, java.util.EnumSet.allOf(NativePadPolicy.ChallengeType.class), clock, random);
    }

    NativeActiveSession(long timeoutMillis, int actionCount, int maxRetries,
            Set<NativePadPolicy.ChallengeType> challengeTypes, LongSupplier clock, SecureRandom random) {
        if (timeoutMillis < 1000 || timeoutMillis > 60000) throw new IllegalArgumentException("Invalid action timeout");
        if (actionCount < 1 || actionCount > 4 || maxRetries < 0 || maxRetries > 5)
            throw new IllegalArgumentException("Invalid action/retry count");
        if (challengeTypes == null || challengeTypes.isEmpty()) throw new IllegalArgumentException("No active challenge types");
        this.clock = clock;
        this.maxRetries = maxRetries;
        startedAt = clock.getAsLong();
        startedAtMillis = System.currentTimeMillis();
        this.timeoutMillis = timeoutMillis;
        timeoutNanos = timeoutMillis * 1_000_000L;
        Action turn = random.nextBoolean() ? Action.TURN_IMAGE_LEFT : Action.TURN_IMAGE_RIGHT;
        boolean blinkFirst = random.nextBoolean();
        actions = new Action[actionCount];
        boolean allowBlink = challengeTypes.contains(NativePadPolicy.ChallengeType.BLINK);
        boolean allowTurn = challengeTypes.contains(NativePadPolicy.ChallengeType.TURN);
        for (int i = 0; i < actionCount; i++) {
            actions[i] = allowBlink && allowTurn ? (((i % 2 == 0) == blinkFirst) ? Action.BLINK : turn)
                    : allowBlink ? Action.BLINK : turn;
        }
    }

    public synchronized State state() {
        expire(); return state;
    }

    public synchronized int completedActions() {
        expire(); return state == State.REJECTED ? 0 : action;
    }

    public int requiredActions() { return actions.length; }
    public synchronized int retriesUsed() { return retries; }
    public long startedAtMillis() { return startedAtMillis; }
    public long timeoutMillis() { return timeoutMillis; }

    /** Immutable claims minted only after exact-frame proof consumption. */
    public static final class Attestation {
        public final long sessionStartedAtMillis, completedAtMillis, sessionTimeoutMillis;
        public final int actionCount, retryLimit, retriesUsed;
        private final String[] actions;

        private Attestation(long started, long completed, long timeout, Action[] actions, int retryLimit, int retries) {
            sessionStartedAtMillis = started; completedAtMillis = completed; sessionTimeoutMillis = timeout;
            actionCount = actions.length; this.retryLimit = retryLimit; retriesUsed = retries;
            this.actions = new String[actions.length];
            for (int i = 0; i < actions.length; i++) {
                this.actions[i] = actions[i] == Action.BLINK ? "BLINK"
                        : actions[i] == Action.TURN_IMAGE_LEFT ? "TURN_LEFT" : "TURN_RIGHT";
            }
        }
        public String[] actionTypes() { return actions.clone(); }
    }

    public synchronized String prompt() {
        expire();
        if (state != State.VERIFYING) return state.name();
        if (!padClear) return "Checking liveness. Keep your face in view";
        if (phase == 0 && action == 0) return "Look straight at the camera with both eyes open";
        if (phase == 0 || (phase == 1 && clock.getAsLong() - actionPromptAt < 2_000_000_000L)) {
            if (actions[action] == Action.BLINK) return "Get ready to blink. Wait for the next instruction.";
            return "Get ready to turn toward the " + (actions[action] == Action.TURN_IMAGE_LEFT ? "LEFT" : "RIGHT")
                    + " side of the preview. Keep facing the camera for now.";
        }
        if (actions[action] == Action.BLINK) return "Blink once, then open both eyes";
        return actions[action] == Action.TURN_IMAGE_LEFT ? "Move your nose toward the left side of the preview, then face the camera" :
                "Move your nose toward the right side of the preview, then face the camera";
    }

    /** Missing/multiple faces invalidate all actions. Call this for failed frame geometry. */
    public synchronized void invalidateFrame() {
        if (state != State.VERIFYING) return;
        if (!restartActions()) return;
        padStreak = 0; padClear = false; padStarted = padLast = null;
    }

    // Charge one retry per interrupted clear-evidence episode, not every missing frame.
    private boolean restartActions() {
        if (padClear || action > 0 || phase > 0) {
            if (retries >= maxRetries) { reject(); return false; }
            retries++;
        }
        padClear = false;
        clearActions();
        return true;
    }

    private void clearActions() {
        action = phase = stable = 0;
        heldSince = 0;
    }

    /** The adapter must derive both observations from this same frame, in this session. */
    public synchronized State observe(long sequence, NativeLandmarkEngine.Observation face,
            NativePadEngine.Decision pad, byte[] exactFrameJpeg) throws Exception {
        expire();
        if (state != State.VERIFYING) return state;
        long now = clock.getAsLong();
        if (sequence <= lastSequence || (observed && now - lastTime < 0)) return reject();
        lastSequence = sequence;
        if (observed && now - lastTime > 1_000_000_000L) invalidateFrame();
        if (state != State.VERIFYING) return state;
        lastTime = now;
        observed = true;
        if (!observePad(pad, now)) return state;
        if (face == null || !Double.isFinite(face.presence) || face.presence < .9 || !Double.isFinite(face.leftEar) || !Double.isFinite(face.rightEar)
                || !Double.isFinite(face.turnRatio)) { invalidateFrame(); return state; }
        boolean open = face.leftEar >= .23 && face.rightEar >= .23;
        boolean neutral = open && Math.abs(face.turnRatio) < .12;
        if (phase == 0) {
            if (hold(neutral, now, 3, 150_000_000L)) { phase = 1; stable = 0; actionPromptAt = now; }
        } else if (phase == 1) {
            // PAD still runs during reading time; movements here earn no action credit.
            if (now - actionPromptAt < 2_000_000_000L) { stable = 0; return state; }
            boolean target = actions[action] == Action.BLINK ? face.leftEar < .18 && face.rightEar < .18 :
                    open && (actions[action] == Action.TURN_IMAGE_LEFT ? face.turnRatio < -.25 : face.turnRatio > .25);
            long duration = actions[action] == Action.BLINK ? 80_000_000L : 150_000_000L;
            if (hold(target, now, 2, duration)) { phase = 2; stable = 0; }
        } else if (hold(neutral, now, 2, 80_000_000L)) {
            action++; phase = stable = 0;
            if (action == actions.length) {
                if (exactFrameJpeg == null || exactFrameJpeg.length < 4 || exactFrameJpeg.length > BoundedMjpegReader.MAX_FRAME_BYTES)
                    return reject();
                candidateDigest = MessageDigest.getInstance("SHA-256").digest(exactFrameJpeg);
                completedAt = now;
                completedAtMillis = System.currentTimeMillis();
                state = State.COMPLETE;
            }
        }
        return state;
    }

    /** Suspect evidence blocks immediately; repeated observations confirm a rejection. */
    private boolean observePad(NativePadEngine.Decision pad, long now) {
        if (pad == null || !Double.isFinite(pad.score) || pad.score < 0 || pad.score > 1) {
            reject(); return false;
        }
        boolean attack = "PRESENTATION_ATTACK".equals(pad.reason) && pad.score <= .45;
        boolean clear = ("PASSIVE_CLEAR".equals(pad.reason) || "ACTIVE_CHALLENGE_REQUIRED".equals(pad.reason))
                && pad.score > .45;
        if (!attack && !clear) { reject(); return false; }
        if (padLast != null && now - padLast > 750_000_000L) invalidateFrame();
        if (state != State.VERIFYING) return false;
        padLast = now;
        if (padStarted == null) padStarted = now;
        if (clear && padClear) return true;
        if (attack && !restartActions()) return false;
        int direction = attack ? -1 : 1;
        if (Integer.signum(padStreak) != direction) {
            padStreak = direction; padHeldSince = now;
        } else padStreak += direction;
        if (attack && padStreak <= -5 && now - padHeldSince >= 500_000_000L) {
            reject(); return false;
        }
        if (clear && padStreak >= 5 && now - padHeldSince >= 250_000_000L) {
            padClear = true; padStarted = null; return true;
        }
        if (now - padStarted >= 10_000_000_000L) reject();
        return false;
    }

    private boolean hold(boolean condition, long now, int frames, long nanos) {
        if (!condition) { stable = 0; return false; }
        if (stable++ == 0) heldSince = now;
        return stable >= frames && now - heldSince >= nanos;
    }
    private void expire() {
        long now = clock.getAsLong();
        if ((state == State.VERIFYING || state == State.COMPLETE)
                && (now - startedAt < 0 || now - startedAt > timeoutNanos
                    || (observed && now - lastTime < 0))) reject();
        if (state == State.COMPLETE && now - completedAt > 2_000_000_000L) reject();
    }
    public synchronized void cancel() { reject(); }
    private State reject() {
        candidateDigest = null; state = State.REJECTED; return state;
    }
    /** One use, exact JPEG bytes, before expiry. No similarity or user-supplied verdict. */
    public synchronized boolean consume(byte[] exactFrameJpeg) throws Exception {
        return consumeAndAttest(exactFrameJpeg) != null;
    }

    /** One-use exact-frame consumption and immutable session claims for the signed SBI result. */
    public synchronized Attestation consumeAndAttest(byte[] exactFrameJpeg) throws Exception {
        expire();
        if (state != State.COMPLETE) return null;
        boolean matches = exactFrameJpeg != null && MessageDigest.isEqual(candidateDigest,
                MessageDigest.getInstance("SHA-256").digest(exactFrameJpeg));
        state = matches ? State.CONSUMED : State.REJECTED;
        candidateDigest = null;
        return matches ? new Attestation(startedAtMillis, completedAtMillis, timeoutMillis,
                actions, maxRetries, retries) : null;
    }
}
