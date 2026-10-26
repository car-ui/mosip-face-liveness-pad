package io.mosip.facepad;

import java.io.IOException;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Reads the standard SBI capture-request customOpts extension and converts the
 * non-sensitive Face PAD settings to the private camera activity's typed extras.
 * The registration client remains authoritative and validates signed evidence
 * against its own current policy after capture.
 */
public final class CameraSbiRequestPolicy {
    public static final String INTENT_ACTION_COUNT = "FacePadActionCount";
    public static final String INTENT_TIMEOUT_SECONDS = "FacePadTimeoutSeconds";
    public static final String INTENT_MAX_RETRIES = "FacePadMaxRetries";
    public static final String INTENT_CHALLENGE_TYPES = "FacePadChallengeTypes";

    private CameraSbiRequestPolicy() { }

    public static NativePadPolicy fromCaptureRequest(Object request, Map<?,?> callerExtras) throws IOException {
        Map<?,?> customOptions = requestCustomOptions(request);
        if (hasPolicyKey(customOptions))
            return NativePadPolicy.fromSbiCustomOptions(normalizeIntentOptions(customOptions));
        if (hasPolicyKey(callerExtras)) return NativePadPolicy.fromSbiCustomOptions(normalizeIntentOptions(callerExtras));
        return NativePadPolicy.forCameraCapture(2,20,2,"blink,turn");
    }

    public static Map<String,Object> toIntentOptions(NativePadPolicy policy) throws IOException {
        if (policy == null || !policy.enabled || !policy.activeEnabled)
            throw new IOException("PAD: active verification is disabled in the caller policy");
        Map<String,Object> options=policy.toSbiCustomOptions();
        Map<String,Object> result=new LinkedHashMap<>();
        result.put(INTENT_ACTION_COUNT,options.get(NativePadPolicy.SBI_ACTION_COUNT));
        result.put(INTENT_TIMEOUT_SECONDS,options.get(NativePadPolicy.SBI_TIMEOUT_SECONDS));
        result.put(INTENT_MAX_RETRIES,options.get(NativePadPolicy.SBI_MAX_RETRIES));
        result.put(INTENT_CHALLENGE_TYPES,options.get(NativePadPolicy.SBI_CHALLENGE_TYPES));
        return result;
    }

    private static Map<?,?> normalizeIntentOptions(Map<?,?> extras) throws IOException {
        Map<String,Object> normalized=new LinkedHashMap<>();
        copyIfPresent(extras,normalized,NativePadPolicy.SBI_ACTION_COUNT,NativePadPolicy.SBI_ACTION_COUNT);
        copyIfPresent(extras,normalized,NativePadPolicy.SBI_TIMEOUT_SECONDS,NativePadPolicy.SBI_TIMEOUT_SECONDS);
        copyIfPresent(extras,normalized,NativePadPolicy.SBI_MAX_RETRIES,NativePadPolicy.SBI_MAX_RETRIES);
        copyIfPresent(extras,normalized,NativePadPolicy.SBI_CHALLENGE_TYPES,NativePadPolicy.SBI_CHALLENGE_TYPES);
        copyIfPresent(extras,normalized,INTENT_ACTION_COUNT,NativePadPolicy.SBI_ACTION_COUNT);
        copyIfPresent(extras,normalized,INTENT_TIMEOUT_SECONDS,NativePadPolicy.SBI_TIMEOUT_SECONDS);
        copyIfPresent(extras,normalized,INTENT_MAX_RETRIES,NativePadPolicy.SBI_MAX_RETRIES);
        copyIfPresent(extras,normalized,INTENT_CHALLENGE_TYPES,NativePadPolicy.SBI_CHALLENGE_TYPES);
        return normalized;
    }

    private static void copyIfPresent(Map<?,?> from, Map<String,Object> to, String source, String target) {
        if (from.containsKey(source)) to.put(target,from.get(source));
    }

    private static boolean hasPolicyKey(Map<?,?> options) {
        if (options == null) return false;
        return options.containsKey(NativePadPolicy.SBI_ACTION_COUNT)
                || options.containsKey(NativePadPolicy.SBI_TIMEOUT_SECONDS)
                || options.containsKey(NativePadPolicy.SBI_MAX_RETRIES)
                || options.containsKey(NativePadPolicy.SBI_CHALLENGE_TYPES)
                || options.containsKey(INTENT_ACTION_COUNT)
                || options.containsKey(INTENT_TIMEOUT_SECONDS)
                || options.containsKey(INTENT_MAX_RETRIES)
                || options.containsKey(INTENT_CHALLENGE_TYPES);
    }

    private static Map<?,?> requestCustomOptions(Object request) throws IOException {
        if (request == null) return null;
        Object raw=null;
        boolean found=false;
        for (String accessor:new String[]{"getCustomOpts","getCustomOptions"}) {
            try {
                Method method=request.getClass().getMethod(accessor);
                raw=method.invoke(request);found=true;break;
            } catch (NoSuchMethodException absent) { }
            catch (Exception failure) { throw new IOException("PAD: cannot read SBI customOpts",failure); }
        }
        if (!found) {
            for (Class<?> type=request.getClass();type!=null && !found;type=type.getSuperclass()) {
                for (String name:new String[]{"customOpts","customOptions"}) {
                    try {
                        Field field=type.getDeclaredField(name);
                        field.setAccessible(true);raw=field.get(request);found=true;break;
                    } catch (NoSuchFieldException absent) { }
                    catch (Exception failure) { throw new IOException("PAD: cannot read SBI customOpts",failure); }
                }
            }
        }
        if (!found || raw == null) return null;
        if (raw instanceof Map<?,?>) return (Map<?,?>)raw;
        if (raw instanceof List<?>) {
            Map<String,Object> converted=new LinkedHashMap<>();
            for (Object item:(List<?>)raw) {
                if (!(item instanceof Map<?,?>)) throw new IOException("PAD: SBI customOpts list contains a non-object");
                for (Map.Entry<?,?> entry:((Map<?,?>)item).entrySet()) {
                    if (!(entry.getKey() instanceof String)) throw new IOException("PAD: SBI customOpts key is not a string");
                    String key=(String)entry.getKey();
                    if (converted.containsKey(key)) throw new IOException("PAD: duplicate SBI customOpts key");
                    converted.put(key,entry.getValue());
                }
            }
            return converted;
        }
        // Some JSON-backed SBI request DTOs expose JSONObject instead of Map.
        try {
            Method toMap=raw.getClass().getMethod("toMap");
            Object converted=toMap.invoke(raw);
            if (converted instanceof Map<?,?>) return (Map<?,?>)converted;
        } catch (NoSuchMethodException absent) { }
        catch (Exception failure) { throw new IOException("PAD: cannot decode SBI customOpts",failure); }
        throw new IOException("PAD: SBI customOpts must be an object");
    }
}
