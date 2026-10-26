import io.mosip.facepad.NativePadPolicy;
import java.io.IOException;
import java.util.*;

/** Configuration parsing and workflow binding; no camera/model accuracy claim. */
public final class NativePadPolicyCheck {
    public static void main(String[] args) throws Exception {
        for(NativePadPolicy.Workflow workflow:NativePadPolicy.Workflow.values()) {
            NativePadPolicy policy=NativePadPolicy.defaults(workflow);
            if(!policy.enabled || !policy.activeEnabled || policy.passiveThreshold!=.85
                    || policy.activeRequired!=(workflow!=NativePadPolicy.Workflow.RESIDENT)
                    || policy.actionCount != (workflow == NativePadPolicy.Workflow.RESIDENT ? 1 : 2)
                    || policy.timeoutSeconds != (workflow == NativePadPolicy.Workflow.RESIDENT ? 15 : 20)
                    || policy.maxRetries != 2
                    || !policy.challengeTypes.equals(EnumSet.allOf(NativePadPolicy.ChallengeType.class)))
                throw new AssertionError("Unsafe default");
        }
        Map<String,String> config=new HashMap<>();
        config.put("mosip.facepad.supervisor.passive.threshold","0.95");
        config.put("mosip.facepad.supervisor.active.action_count","3");
        config.put("mosip.facepad.supervisor.active.timeout_seconds","30");
        config.put("mosip.facepad.supervisor.active.max_retries","1");
        config.put("mosip.facepad.supervisor.active.challenge_types","blink");
        NativePadPolicy supervisor=NativePadPolicy.read(config::get,NativePadPolicy.Workflow.SUPERVISOR);
        if(supervisor.passiveThreshold!=.95 || !supervisor.activeRequired
                || supervisor.actionCount != 3 || supervisor.timeoutSeconds != 30 || supervisor.maxRetries != 1
                || !supervisor.challengeTypes.equals(EnumSet.of(NativePadPolicy.ChallengeType.BLINK)))
            throw new AssertionError("Workflow override lost");
        if(supervisor.sameAs(NativePadPolicy.defaults(NativePadPolicy.Workflow.OPERATOR)))throw new AssertionError("Roles confused");
        if(!supervisor.sameAs(NativePadPolicy.read(config::get,NativePadPolicy.Workflow.SUPERVISOR)))throw new AssertionError("Snapshot mismatch");
        for(String value:new String[]{"NaN","Infinity","0.45","1",""," .9","garbage"}) {
            config.put("mosip.facepad.supervisor.passive.threshold",value);
            try {NativePadPolicy.read(config::get,NativePadPolicy.Workflow.SUPERVISOR);throw new AssertionError("Bad threshold accepted");}
            catch(IOException expected) { }
        }
        config.remove("mosip.facepad.supervisor.passive.threshold");

        // Test alternate property keys and bounds for action_count, timeout_seconds, and max_retries
        config.clear();
        config.put("mosip.facepad.operator.action.count", "4");
        config.put("mosip.facepad.operator.timeout_seconds", "45");
        config.put("mosip.facepad.operator.max_retries", "0");
        config.put("mosip.facepad.operator.challenge.types", "turn");
        NativePadPolicy operator = NativePadPolicy.read(config::get, NativePadPolicy.Workflow.OPERATOR);
        if (operator.actionCount != 4 || operator.timeoutSeconds != 45 || operator.maxRetries != 0
                || !operator.challengeTypes.equals(EnumSet.of(NativePadPolicy.ChallengeType.TURN)))
            throw new AssertionError("Alternate configuration keys failed");

        NativePadPolicy camera=NativePadPolicy.forCameraCapture(3,30,1,"blink");
        if(camera.actionCount!=3 || camera.timeoutSeconds!=30 || camera.maxRetries!=1
                || !camera.activeRequired
                || !camera.challengeTypes.equals(EnumSet.of(NativePadPolicy.ChallengeType.BLINK)))
            throw new AssertionError("Camera capture policy was not applied");
        NativePadPolicy cached=NativePadPolicy.read(config::get,NativePadPolicy.Workflow.OPERATOR);
        Map<String,Object> requestOptions=cached.toSbiCustomOptions();
        NativePadPolicy roundTrip=NativePadPolicy.fromSbiCustomOptions(requestOptions);
        if(roundTrip.actionCount!=cached.actionCount || roundTrip.timeoutSeconds!=cached.timeoutSeconds
                || roundTrip.maxRetries!=cached.maxRetries || !roundTrip.challengeTypes.equals(cached.challengeTypes))
            throw new AssertionError("Cached policy changed at the standard SBI customOpts boundary");
        List<Map<?,?>> invalidOptions=new ArrayList<>();
        invalidOptions.add(Collections.emptyMap());
        Map<String,Object> fractionalCount=new HashMap<>(requestOptions);
        fractionalCount.put(NativePadPolicy.SBI_ACTION_COUNT,2.5);
        invalidOptions.add(fractionalCount);
        Map<String,Object> stringTimeout=new HashMap<>(requestOptions);
        stringTimeout.put(NativePadPolicy.SBI_TIMEOUT_SECONDS,"30.0");
        invalidOptions.add(stringTimeout);
        Map<String,Object> malformedPool=new HashMap<>(requestOptions);
        malformedPool.put(NativePadPolicy.SBI_CHALLENGE_TYPES,"blink, turn");
        invalidOptions.add(malformedPool);
        for(Map<?,?> invalid:invalidOptions) {
            try { NativePadPolicy.fromSbiCustomOptions(invalid); throw new AssertionError("Invalid SBI policy accepted"); }
            catch(IOException expected) { }
        }
        for(String badTypes:new String[]{null,"","turn, blink","smile"}) {
            try {NativePadPolicy.forCameraCapture(2,20,2,badTypes);throw new AssertionError("Invalid camera challenge pool accepted");}
            catch(IOException expected) { }
        }
        for(int[] invalid:new int[][]{{0,20,2},{5,20,2},{2,4,2},{2,61,2},{2,20,-1},{2,20,6}}) {
            try {NativePadPolicy.forCameraCapture(invalid[0],invalid[1],invalid[2],"blink,turn");throw new AssertionError("Invalid camera policy accepted");}
            catch(IOException expected) { }
        }

        for (String badAction : new String[]{"0", "5", "-1", "abc", " 2", ""}) {
            config.put("mosip.facepad.operator.active.action_count", badAction);
            try { NativePadPolicy.read(config::get, NativePadPolicy.Workflow.OPERATOR); throw new AssertionError("Bad action_count accepted: " + badAction); }
            catch (IOException expected) {}
        }
        config.remove("mosip.facepad.operator.active.action_count");

        for (String badTimeout : new String[]{"4", "61", "0", "-1", "abc", " 15", ""}) {
            config.put("mosip.facepad.operator.active.timeout_seconds", badTimeout);
            try { NativePadPolicy.read(config::get, NativePadPolicy.Workflow.OPERATOR); throw new AssertionError("Bad timeout accepted: " + badTimeout); }
            catch (IOException expected) {}
        }
        config.remove("mosip.facepad.operator.active.timeout_seconds");

        for (String badRetries : new String[]{"-1", "6", "abc", " 2", ""}) {
            config.put("mosip.facepad.operator.active.max_retries", badRetries);
            try { NativePadPolicy.read(config::get, NativePadPolicy.Workflow.OPERATOR); throw new AssertionError("Bad max_retries accepted: " + badRetries); }
            catch (IOException expected) {}
        }
        config.remove("mosip.facepad.operator.active.max_retries");

        config.remove("mosip.facepad.operator.challenge.types");
        for (String badTypes : new String[]{"", "blink,", "blink,blink", "BLINK", "blink, turn", "smile"}) {
            config.put("mosip.facepad.operator.active.challenge_types",badTypes);
            try {NativePadPolicy.read(config::get,NativePadPolicy.Workflow.OPERATOR);throw new AssertionError("Bad challenge pool accepted: "+badTypes);}
            catch(IOException expected) { }
        }
        config.remove("mosip.facepad.operator.active.challenge_types");

        config.clear();config.put("mosip.facepad.operator.active.required","false");
        try {NativePadPolicy.read(config::get,NativePadPolicy.Workflow.OPERATOR);throw new AssertionError("Mandatory actions disabled");}
        catch(IOException expected) { }
        config.clear();config.put("mosip.facepad.operator.active.enabled","false");
        try {NativePadPolicy.read(config::get,NativePadPolicy.Workflow.OPERATOR);throw new AssertionError("Active disabled while mandatory");}
        catch(IOException expected) { }
        config.clear();config.put("mosip.facepad.enabled","false");
        if(NativePadPolicy.read(config::get,NativePadPolicy.Workflow.RESIDENT).enabled)throw new AssertionError("Disabled policy ignored");
        for(String value:new String[]{"FALSE","0"," true",""}) {
            config.put("mosip.facepad.enabled",value);
            try {NativePadPolicy.read(config::get,NativePadPolicy.Workflow.RESIDENT);throw new AssertionError("Malformed boolean accepted");}
            catch(IOException expected) { }
        }
        System.out.println("PASS native policy: cached workflow parsing, strict SBI customOpts round-trip, defaults, immutable snapshots, finite thresholds, strict booleans, challenge pools, action/timeout/retry bounds, and mandatory-action protection");
    }
}
