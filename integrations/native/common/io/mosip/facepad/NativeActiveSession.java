package io.mosip.facepad;

import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.function.LongSupplier;

/** Session-bound action progression for trusted frame adapters and exact-image consumers. */
public final class NativeActiveSession {
    public enum State { VERIFYING, COMPLETE, REJECTED, CONSUMED }
    private enum Action { BLINK, TURN_IMAGE_LEFT, TURN_IMAGE_RIGHT }
    private final LongSupplier clock;
    private final long startedAt, timeoutNanos;
    private final Action[] actions;
    private State state = State.VERIFYING;
    private int action, phase, stable;
    private long lastSequence = -1, lastTime = -1, heldSince;
    private boolean observed;
    private long completedAt;
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
        if (timeoutMillis < 1000 || timeoutMillis > 60000) throw new IllegalArgumentException("Invalid action timeout");
        this.clock = clock;
        startedAt = clock.getAsLong();
        timeoutNanos = timeoutMillis * 1_000_000L;
        Action turn = random.nextBoolean() ? Action.TURN_IMAGE_LEFT : Action.TURN_IMAGE_RIGHT;
        actions = random.nextBoolean() ? new Action[]{Action.BLINK,turn} : new Action[]{turn,Action.BLINK};
    }

    public synchronized State state() {
        expire(); return state;
    }

    public synchronized int completedActions() {
        expire(); return state == State.REJECTED ? 0 : action;
    }

    public int requiredActions() { return actions.length; }

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
        padStreak = 0; padClear = false; padStarted = padLast = null;
        clearActions();
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
        padLast = now;
        if (padStarted == null) padStarted = now;
        if (clear && padClear) return true;
        if (attack) { padClear = false; clearActions(); }
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
        expire();
        if (state != State.COMPLETE) return false;
        boolean matches = exactFrameJpeg != null && MessageDigest.isEqual(candidateDigest,
                MessageDigest.getInstance("SHA-256").digest(exactFrameJpeg));
        state = matches ? State.CONSUMED : State.REJECTED;
        candidateDigest = null;
        return matches;
    }
}
