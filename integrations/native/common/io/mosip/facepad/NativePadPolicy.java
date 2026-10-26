package io.mosip.facepad;

import java.io.IOException;
import java.util.Collections;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;

/** Immutable research policy read from the host client's existing configuration cache. */
public final class NativePadPolicy {
    public static final String SBI_ACTION_COUNT = "facePadActionCount";
    public static final String SBI_TIMEOUT_SECONDS = "facePadTimeoutSeconds";
    public static final String SBI_MAX_RETRIES = "facePadMaxRetries";
    public static final String SBI_CHALLENGE_TYPES = "facePadChallengeTypes";
    public enum Workflow { RESIDENT, OPERATOR, SUPERVISOR }
    public enum ChallengeType { BLINK, TURN }
    public final Workflow workflow;
    public final boolean enabled, activeEnabled, activeRequired;
    public final double passiveThreshold;
    public final int actionCount;
    public final int timeoutSeconds;
    public final int maxRetries;
    public final Set<ChallengeType> challengeTypes;

    private NativePadPolicy(Workflow workflow, boolean enabled, boolean activeEnabled,
                            boolean activeRequired, double passiveThreshold,
                            int actionCount, int timeoutSeconds, int maxRetries,
                            Set<ChallengeType> challengeTypes) throws IOException {
        if (workflow == null || !Double.isFinite(passiveThreshold) || passiveThreshold < .46 || passiveThreshold > .99)
            throw new IOException("PAD: invalid native policy");
        if ((workflow != Workflow.RESIDENT && !activeRequired) || (activeRequired && !activeEnabled))
            throw new IOException("PAD: mandatory active verification cannot be disabled");
        if (actionCount < 1 || actionCount > 4)
            throw new IOException("PAD: invalid action count");
        if (timeoutSeconds < 5 || timeoutSeconds > 60)
            throw new IOException("PAD: invalid timeout");
        if (maxRetries < 0 || maxRetries > 5)
            throw new IOException("PAD: invalid retry limit");
        if (challengeTypes == null || challengeTypes.isEmpty())
            throw new IOException("PAD: at least one native challenge type is required");
        this.workflow = workflow; this.enabled = enabled; this.activeEnabled = activeEnabled;
        this.activeRequired = activeRequired; this.passiveThreshold = passiveThreshold;
        this.actionCount = actionCount; this.timeoutSeconds = timeoutSeconds; this.maxRetries = maxRetries;
        this.challengeTypes = Collections.unmodifiableSet(EnumSet.copyOf(challengeTypes));
    }

    public static NativePadPolicy defaults(Workflow workflow) {
        if (workflow == null) throw new IllegalArgumentException("Native workflow is required");
        try { return read(key -> null, workflow); }
        catch(IOException impossible) { throw new IllegalStateException(impossible); }
    }

    /** Strict camera-SBI request policy. The client must independently check returned claims. */
    public static NativePadPolicy forCameraCapture(int actionCount, int timeoutSeconds,
                                                    int maxRetries, String challengeTypes) throws IOException {
        if (challengeTypes == null) throw new IOException("PAD: camera challenge pool is required");
        try {
            return new NativePadPolicy(Workflow.OPERATOR, true, true, true, .85,
                    actionCount, timeoutSeconds, maxRetries, challengeTypes(challengeTypes));
        } catch (RuntimeException failure) {
            throw new IOException("PAD: invalid camera capture policy", failure);
        }
    }

    /**
     * Convert the already validated client policy to documented, non-sensitive SBI
     * customOpts. The caller must use the workflow policy read from its current cache.
     */
    public Map<String,Object> toSbiCustomOptions() {
        Map<String,Object> options = new LinkedHashMap<>();
        options.put(SBI_ACTION_COUNT, actionCount);
        options.put(SBI_TIMEOUT_SECONDS, timeoutSeconds);
        options.put(SBI_MAX_RETRIES, maxRetries);
        StringBuilder types = new StringBuilder();
        for (ChallengeType type : challengeTypes) {
            if (types.length() > 0) types.append(',');
            types.append(type == ChallengeType.BLINK ? "blink" : "turn");
        }
        options.put(SBI_CHALLENGE_TYPES, types.toString());
        return Collections.unmodifiableMap(options);
    }

    /** Read a complete policy from the SBI customOpts map; partial claims fail closed. */
    public static NativePadPolicy fromSbiCustomOptions(Map<?,?> options) throws IOException {
        if (options == null || !options.containsKey(SBI_ACTION_COUNT)
                || !options.containsKey(SBI_TIMEOUT_SECONDS)
                || !options.containsKey(SBI_MAX_RETRIES)
                || !options.containsKey(SBI_CHALLENGE_TYPES))
            throw new IOException("PAD: SBI capture policy is incomplete");
        try {
            int actions = exactInteger(options.get(SBI_ACTION_COUNT), SBI_ACTION_COUNT);
            int timeout = exactInteger(options.get(SBI_TIMEOUT_SECONDS), SBI_TIMEOUT_SECONDS);
            int retries = exactInteger(options.get(SBI_MAX_RETRIES), SBI_MAX_RETRIES);
            Object rawTypes = options.get(SBI_CHALLENGE_TYPES);
            if (!(rawTypes instanceof String)) throw new IOException("PAD: invalid SBI challenge pool");
            return forCameraCapture(actions, timeout, retries, (String) rawTypes);
        } catch (IOException failure) { throw failure; }
        catch (RuntimeException failure) { throw new IOException("PAD: invalid SBI capture policy", failure); }
    }

    private static int exactInteger(Object value, String name) throws IOException {
        if (value instanceof String) {
            String text=(String)value;
            if (!text.matches("-?(0|[1-9][0-9]*)"))
                throw new IOException("PAD: invalid SBI " + name);
            try { return Integer.parseInt(text); }
            catch (NumberFormatException failure) { throw new IOException("PAD: invalid SBI " + name,failure); }
        }
        if (!(value instanceof Number)) throw new IOException("PAD: invalid SBI " + name);
        Number number = (Number) value;
        double decimal = number.doubleValue();
        long integral = number.longValue();
        if (!Double.isFinite(decimal) || decimal != (double) integral
                || integral < Integer.MIN_VALUE || integral > Integer.MAX_VALUE)
            throw new IOException("PAD: invalid SBI " + name);
        return (int) integral;
    }

    public static NativePadPolicy read(Function<String,String> values, Workflow workflow) throws IOException {
        if (values == null || workflow == null) throw new IOException("PAD: native configuration unavailable");
        String prefix = "mosip.facepad." + workflow.name().toLowerCase(java.util.Locale.ROOT) + ".";
        try {
            boolean enabled = bool(values.apply("mosip.facepad.enabled"), true);
            boolean activeEnabled = bool(values.apply(prefix + "active.enabled"), true);
            boolean activeRequired = bool(values.apply(prefix + "active.required"), workflow != Workflow.RESIDENT);
            String threshold = values.apply(prefix + "passive.threshold");
            double score = threshold == null ? .85 : Double.parseDouble(bounded(threshold));
            int defaultActions = workflow == Workflow.RESIDENT ? 1 : 2;
            int defaultTimeout = workflow == Workflow.RESIDENT ? 15 : 20;
            int actions = integer(first(values, prefix + "active.action_count", prefix + "action.count"), defaultActions);
            int timeout = integer(first(values, prefix + "active.timeout_seconds", prefix + "timeout_seconds"), defaultTimeout);
            int retries = integer(first(values, prefix + "active.max_retries", prefix + "max_retries"), 2);
            String types = first(values, prefix + "active.challenge_types", prefix + "challenge.types");
            Set<ChallengeType> pool = challengeTypes(types);
            return new NativePadPolicy(workflow, enabled, activeEnabled, activeRequired, score, actions, timeout, retries, pool);
        } catch(IOException failure) { throw failure; }
        catch(RuntimeException failure) { throw new IOException("PAD: invalid native configuration", failure); }
    }

    private static String first(Function<String,String> values, String k1, String k2) {
        String v = values.apply(k1);
        return v != null ? v : values.apply(k2);
    }

    private static int integer(String value, int fallback) throws IOException {
        if (value == null) return fallback;
        String b = bounded(value);
        try {
            return Integer.parseInt(b);
        } catch (NumberFormatException e) {
            throw new IOException("PAD: invalid native integer configuration value", e);
        }
    }

    private static Set<ChallengeType> challengeTypes(String value) throws IOException {
        if (value == null) return EnumSet.allOf(ChallengeType.class);
        String b = bounded(value);
        EnumSet<ChallengeType> result = EnumSet.noneOf(ChallengeType.class);
        for (String token : b.split(",", -1)) {
            if ("blink".equals(token)) {
                if (!result.add(ChallengeType.BLINK)) throw new IOException("PAD: duplicate native challenge type");
            } else if ("turn".equals(token)) {
                if (!result.add(ChallengeType.TURN)) throw new IOException("PAD: duplicate native challenge type");
            } else throw new IOException("PAD: unsupported native challenge type");
        }
        if (result.isEmpty()) throw new IOException("PAD: at least one native challenge type is required");
        return result;
    }

    private static String bounded(String value) throws IOException {
        if (value.length() == 0 || value.length() > 32 || !value.equals(value.trim()))
            throw new IOException("PAD: invalid native configuration value");
        return value;
    }

    private static boolean bool(String value, boolean fallback) throws IOException {
        if (value == null) return fallback;
        if ("true".equals(bounded(value))) return true;
        if ("false".equals(value)) return false;
        throw new IOException("PAD: native boolean must be true or false");
    }

    public boolean sameAs(NativePadPolicy other) {
        return other != null && workflow == other.workflow && enabled == other.enabled
            && activeEnabled == other.activeEnabled && activeRequired == other.activeRequired
            && Double.compare(passiveThreshold, other.passiveThreshold) == 0
            && actionCount == other.actionCount && timeoutSeconds == other.timeoutSeconds
            && maxRetries == other.maxRetries && challengeTypes.equals(other.challengeTypes);
    }
}

