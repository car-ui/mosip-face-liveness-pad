package io.mosip.facepad;

import java.io.IOException;
import java.util.function.Function;

/** Immutable research policy read from the host client's existing configuration cache. */
public final class NativePadPolicy {
    public enum Workflow { RESIDENT, OPERATOR, SUPERVISOR }
    public final Workflow workflow;
    public final boolean enabled, activeEnabled, activeRequired;
    public final double passiveThreshold;
    public final int actionCount;
    public final int timeoutSeconds;
    public final int maxRetries;

    private NativePadPolicy(Workflow workflow, boolean enabled, boolean activeEnabled,
                            boolean activeRequired, double passiveThreshold,
                            int actionCount, int timeoutSeconds, int maxRetries) throws IOException {
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
        this.workflow = workflow; this.enabled = enabled; this.activeEnabled = activeEnabled;
        this.activeRequired = activeRequired; this.passiveThreshold = passiveThreshold;
        this.actionCount = actionCount; this.timeoutSeconds = timeoutSeconds; this.maxRetries = maxRetries;
    }

    public static NativePadPolicy defaults(Workflow workflow) {
        if (workflow == null) throw new IllegalArgumentException("Native workflow is required");
        try { return read(key -> null, workflow); }
        catch(IOException impossible) { throw new IllegalStateException(impossible); }
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
            return new NativePadPolicy(workflow, enabled, activeEnabled, activeRequired, score, actions, timeout, retries);
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
            && maxRetries == other.maxRetries;
    }
}

