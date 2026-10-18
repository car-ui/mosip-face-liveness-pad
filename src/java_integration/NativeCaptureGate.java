package io.mosip.registration.liveness;

import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

/**
 * Portable Java 8 policy component for Desktop/Android integration work.
 * Call from a trusted frame-processing adapter, never from a user-supplied JSON verdict.
 * This component does not perform face matching or PAD inference.
 */
public final class NativeCaptureGate {
    public enum State { VERIFYING, ACCEPTED, REJECTED, CONSUMED }
    private final String session = UUID.randomUUID().toString();
    private final int requiredChallenges;
    private final long deadlineNanos;
    private final Set<String> completed = new HashSet<String>();
    private long lastFrame = -1;
    private State state = State.VERIFYING;
    private byte[] acceptedDigest;

    public NativeCaptureGate(int requiredChallenges, long timeoutMillis) {
        if (requiredChallenges < 0 || requiredChallenges > 6 || timeoutMillis < 1 || timeoutMillis > 60000)
            throw new IllegalArgumentException("Invalid capture policy");
        this.requiredChallenges = requiredChallenges;
        this.deadlineNanos = System.nanoTime() + timeoutMillis * 1000000L;
    }

    public String sessionId() { return session; }
    public synchronized State state() { return state; }

    /** An uncertain frame may progress actions, but an attack/error always terminates. */
    public synchronized boolean observe(String sessionId, long frameSequence, boolean singleFaceQuality,
            boolean padAvailable, boolean attack, boolean passivePassed, String verifiedChallengeId,
            byte[] candidateJpeg) throws Exception {
        if (state != State.VERIFYING) return false;
        if (!session.equals(sessionId) || frameSequence <= lastFrame || System.nanoTime() > deadlineNanos ||
                !singleFaceQuality || !padAvailable || attack) {
            state = State.REJECTED;
            completed.clear();
            return false;
        }
        lastFrame = frameSequence;
        if (verifiedChallengeId != null && !verifiedChallengeId.isEmpty()) completed.add(verifiedChallengeId);
        boolean actionsPassed = requiredChallenges > 0 && completed.size() >= requiredChallenges;
        if ((actionsPassed || (requiredChallenges == 0 && passivePassed)) && candidateJpeg != null && candidateJpeg.length > 0) {
            acceptedDigest = MessageDigest.getInstance("SHA-256").digest(candidateJpeg);
            state = State.ACCEPTED;
            return true;
        }
        return false;
    }

    /** The client can accept this exact payload once, only in the originating session. */
    public synchronized boolean consume(String sessionId, byte[] jpeg) throws Exception {
        if (state != State.ACCEPTED) return false;
        boolean valid = session.equals(sessionId) && jpeg != null && System.nanoTime() <= deadlineNanos &&
                MessageDigest.isEqual(acceptedDigest, MessageDigest.getInstance("SHA-256").digest(jpeg));
        state = valid ? State.CONSUMED : State.REJECTED;
        acceptedDigest = null;
        return valid;
    }
}
