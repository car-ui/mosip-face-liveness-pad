import io.mosip.facepad.CameraSbiRequestPolicy;
import io.mosip.facepad.NativePadPolicy;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/** Request-boundary checks; simulated DTOs are not an official-client capture test. */
public final class CameraSbiRequestPolicyCheck {
    public static final class CaptureRequest {
        private final Object customOpts;
        CaptureRequest(Object customOpts) { this.customOpts=customOpts; }
        public Object getCustomOpts() { return customOpts; }
    }

    public static void main(String[] args) throws Exception {
        NativePadPolicy configured=NativePadPolicy.read(key -> {
            if("mosip.facepad.operator.active.action_count".equals(key))return "3";
            if("mosip.facepad.operator.active.timeout_seconds".equals(key))return "35";
            if("mosip.facepad.operator.active.max_retries".equals(key))return "1";
            if("mosip.facepad.operator.active.challenge_types".equals(key))return "blink";
            return null;
        },NativePadPolicy.Workflow.OPERATOR);
        CaptureRequest request=new CaptureRequest(configured.toSbiCustomOptions());
        NativePadPolicy received=CameraSbiRequestPolicy.fromCaptureRequest(request,null);
        require(received.actionCount==3 && received.timeoutSeconds==35 && received.maxRetries==1
                && received.challengeTypes.equals(configured.challengeTypes),"SBI customOpts policy did not round-trip");
        java.util.List<Map<String,String>> daoOptions=new java.util.ArrayList<>();
        for(Map.Entry<String,Object> entry:configured.toSbiCustomOptions().entrySet()) {
            Map<String,String> item=new HashMap<>();item.put(entry.getKey(),String.valueOf(entry.getValue()));daoOptions.add(item);
        }
        NativePadPolicy fromDao=CameraSbiRequestPolicy.fromCaptureRequest(new CaptureRequest(daoOptions),null);
        require(fromDao.actionCount==configured.actionCount && fromDao.timeoutSeconds==configured.timeoutSeconds
                && fromDao.maxRetries==configured.maxRetries && fromDao.challengeTypes.equals(configured.challengeTypes),
                "Reference SBI DAO list-of-maps customOpts did not parse");
        Map<String,Object> intent=CameraSbiRequestPolicy.toIntentOptions(received);
        require(Integer.valueOf(3).equals(intent.get(CameraSbiRequestPolicy.INTENT_ACTION_COUNT)),"Action count extra missing");
        require("blink".equals(intent.get(CameraSbiRequestPolicy.INTENT_CHALLENGE_TYPES)),"Challenge pool extra missing");

        Map<String,Object> caller=new HashMap<>();
        caller.put(CameraSbiRequestPolicy.INTENT_ACTION_COUNT,2);
        caller.put(CameraSbiRequestPolicy.INTENT_TIMEOUT_SECONDS,25);
        caller.put(CameraSbiRequestPolicy.INTENT_MAX_RETRIES,0);
        caller.put(CameraSbiRequestPolicy.INTENT_CHALLENGE_TYPES,"turn");
        NativePadPolicy fromCaller=CameraSbiRequestPolicy.fromCaptureRequest(null,caller);
        require(fromCaller.actionCount==2 && fromCaller.timeoutSeconds==25 && fromCaller.maxRetries==0
                && fromCaller.challengeTypes.contains(NativePadPolicy.ChallengeType.TURN),"Caller extras fallback failed");
        NativePadPolicy defaults=CameraSbiRequestPolicy.fromCaptureRequest(null,null);
        require(defaults.actionCount==2 && defaults.timeoutSeconds==20 && defaults.maxRetries==2,
                "Backward-compatible defaults changed");

        Map<String,Object> partial=new HashMap<>();partial.put(NativePadPolicy.SBI_ACTION_COUNT,3);
        try {
            CameraSbiRequestPolicy.fromCaptureRequest(new CaptureRequest(partial),caller);
            throw new AssertionError("Partial request policy fell back to caller defaults");
        } catch(IOException expected) { }
        try {
            NativePadPolicy disabled=NativePadPolicy.read(key ->
                "mosip.facepad.enabled".equals(key)?"false":null,NativePadPolicy.Workflow.OPERATOR);
            CameraSbiRequestPolicy.toIntentOptions(disabled);
            throw new AssertionError("Disabled liveness policy was forwarded to camera");
        } catch(IOException expected) { }
        System.out.println("PASS SBI capture policy handoff: object and DAO list-of-maps customOpts, caller extras, defaults, and fail-closed malformed or disabled policies");
    }

    private static void require(boolean value,String message) {
        if(!value)throw new AssertionError(message);
    }
}
