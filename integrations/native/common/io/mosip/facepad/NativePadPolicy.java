package io.mosip.facepad;

import java.io.IOException;
import java.util.function.Function;

/** Immutable research policy read from the host client's existing configuration cache. */
public final class NativePadPolicy {
    public enum Workflow { RESIDENT, OPERATOR, SUPERVISOR }
    public final Workflow workflow;
    public final boolean enabled, activeEnabled, activeRequired;
    public final double passiveThreshold;

    private NativePadPolicy(Workflow workflow,boolean enabled,boolean activeEnabled,
                            boolean activeRequired,double passiveThreshold) throws IOException {
        if (workflow == null || !Double.isFinite(passiveThreshold) || passiveThreshold < .46 || passiveThreshold > .99)
            throw new IOException("PAD: invalid native policy");
        if ((workflow != Workflow.RESIDENT && !activeRequired) || (activeRequired && !activeEnabled))
            throw new IOException("PAD: mandatory active verification cannot be disabled");
        this.workflow=workflow;this.enabled=enabled;this.activeEnabled=activeEnabled;
        this.activeRequired=activeRequired;this.passiveThreshold=passiveThreshold;
    }

    public static NativePadPolicy defaults(Workflow workflow) {
        if (workflow == null) throw new IllegalArgumentException("Native workflow is required");
        try { return read(key -> null,workflow); }
        catch(IOException impossible) { throw new IllegalStateException(impossible); }
    }

    public static NativePadPolicy read(Function<String,String> values,Workflow workflow) throws IOException {
        if (values == null || workflow == null) throw new IOException("PAD: native configuration unavailable");
        String prefix="mosip.facepad."+workflow.name().toLowerCase(java.util.Locale.ROOT)+".";
        try {
            boolean enabled=bool(values.apply("mosip.facepad.enabled"),true);
            boolean activeEnabled=bool(values.apply(prefix+"active.enabled"),true);
            boolean activeRequired=bool(values.apply(prefix+"active.required"),workflow != Workflow.RESIDENT);
            String threshold=values.apply(prefix+"passive.threshold");
            double score=threshold == null ? .85 : Double.parseDouble(bounded(threshold));
            return new NativePadPolicy(workflow,enabled,activeEnabled,activeRequired,score);
        } catch(IOException failure) { throw failure; }
        catch(RuntimeException failure) { throw new IOException("PAD: invalid native configuration",failure); }
    }

    private static String bounded(String value) throws IOException {
        if (value.length() == 0 || value.length() > 32 || !value.equals(value.trim()))
            throw new IOException("PAD: invalid native configuration value");
        return value;
    }
    private static boolean bool(String value,boolean fallback) throws IOException {
        if (value == null) return fallback;
        if ("true".equals(bounded(value))) return true;
        if ("false".equals(value)) return false;
        throw new IOException("PAD: native boolean must be true or false");
    }
    public boolean sameAs(NativePadPolicy other) {
        return other != null && workflow == other.workflow && enabled == other.enabled
            && activeEnabled == other.activeEnabled && activeRequired == other.activeRequired
            && Double.compare(passiveThreshold,other.passiveThreshold) == 0;
    }
}
