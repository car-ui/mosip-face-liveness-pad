import io.mosip.facepad.NativePadPolicy;
import java.io.IOException;
import java.util.*;

/** Configuration parsing and workflow binding; no camera/model accuracy claim. */
public final class NativePadPolicyCheck {
    public static void main(String[] args) throws Exception {
        for(NativePadPolicy.Workflow workflow:NativePadPolicy.Workflow.values()) {
            NativePadPolicy policy=NativePadPolicy.defaults(workflow);
            if(!policy.enabled || !policy.activeEnabled || policy.passiveThreshold!=.85
                    || policy.activeRequired!=(workflow!=NativePadPolicy.Workflow.RESIDENT))throw new AssertionError("Unsafe default");
        }
        Map<String,String> config=new HashMap<>();
        config.put("mosip.facepad.supervisor.passive.threshold","0.95");
        NativePadPolicy supervisor=NativePadPolicy.read(config::get,NativePadPolicy.Workflow.SUPERVISOR);
        if(supervisor.passiveThreshold!=.95 || !supervisor.activeRequired)throw new AssertionError("Workflow override lost");
        if(supervisor.sameAs(NativePadPolicy.defaults(NativePadPolicy.Workflow.OPERATOR)))throw new AssertionError("Roles confused");
        if(!supervisor.sameAs(NativePadPolicy.read(config::get,NativePadPolicy.Workflow.SUPERVISOR)))throw new AssertionError("Snapshot mismatch");
        for(String value:new String[]{"NaN","Infinity","0.45","1",""," .9","garbage"}) {
            config.put("mosip.facepad.supervisor.passive.threshold",value);
            try {NativePadPolicy.read(config::get,NativePadPolicy.Workflow.SUPERVISOR);throw new AssertionError("Bad threshold accepted");}
            catch(IOException expected) { }
        }
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
        System.out.println("PASS native cached-policy parsing: defaults, role overrides, immutable snapshots, finite thresholds, strict booleans and mandatory-action protection");
    }
}
