package io.mosip.facepad;

import java.security.SecureRandom;
import java.util.concurrent.atomic.AtomicLong;

/** Synthetic geometry fixture for SBI evidence serialization tests; it is not camera evidence. */
public final class CameraEvidenceFixture {
    private static final byte[] JPEG={(byte)255,(byte)216,1,2,(byte)255,(byte)217};
    private CameraEvidenceFixture() { }

    public static NativeActiveSession.Attestation completedSession() throws Exception {
        return completedSession(NativePadPolicy.defaults(NativePadPolicy.Workflow.OPERATOR));
    }

    public static NativeActiveSession.Attestation completedSession(NativePadPolicy policy) throws Exception {
        AtomicLong clock=new AtomicLong();
        NativeActiveSession session=new NativeActiveSession(policy.timeoutSeconds*1000L,
                policy.actionCount,policy.maxRetries,policy.challengeTypes,clock::get,new SecureRandom() {
            @Override public boolean nextBoolean() { return true; }
        });
        long sequence=0;
        for(int i=0;i<7;i++) {clock.addAndGet(100_000_000L);session.observe(++sequence,geometry(.3,0),clear(),JPEG);}
        for(int action=0;action<policy.actionCount;action++) {
            if(action>0) for(int i=0;i<3;i++) {clock.addAndGet(100_000_000L);session.observe(++sequence,geometry(.3,0),clear(),JPEG);}
            for(int i=0;i<20;i++) {clock.addAndGet(100_000_000L);session.observe(++sequence,geometry(.3,0),clear(),JPEG);}
            String instruction=session.prompt();
            double ear,turn;
            if(instruction.startsWith("Blink once")) {ear=.1;turn=0;}
            else if(instruction.startsWith("Move your nose toward the left")) {ear=.3;turn=-.4;}
            else if(instruction.startsWith("Move your nose toward the right")) {ear=.3;turn=.4;}
            else throw new AssertionError("Unexpected fixture instruction: "+instruction);
            for(int i=0;i<3;i++) {
                clock.addAndGet(100_000_000L);
                session.observe(++sequence,geometry(ear,turn),clear(),JPEG);
            }
            for(int i=0;i<2;i++) {clock.addAndGet(100_000_000L);session.observe(++sequence,geometry(.3,0),clear(),JPEG);}
        }
        if(session.state()!=NativeActiveSession.State.COMPLETE)throw new AssertionError("Synthetic action fixture did not complete");
        return session.consumeAndAttest(JPEG);
    }

    private static NativePadEngine.Decision clear() { return new NativePadEngine.Decision(true,"PASSIVE_CLEAR",.99); }
    private static NativeLandmarkEngine.Observation geometry(double ear,double turn) throws Exception {
        float[] points=new float[478*3];
        int[][] eyes={{33,160,158,133,153,144},{362,385,387,263,373,380}};
        for(int i=0;i<2;i++) {
            int[] ids=eyes[i];double x=i==0?80:156,height=ear*20;
            double[][] xy={{x,100},{x+5,100-height/2},{x+15,100-height/2},{x+20,100},
                {x+15,100+height/2},{x+5,100+height/2}};
            for(int j=0;j<6;j++) {points[ids[j]*3]=(float)xy[j][0];points[ids[j]*3+1]=(float)xy[j][1];}
        }
        points[3]=(float)(128+turn*48);points[4]=120;
        return new NativeLandmarkEngine.Observation(points,.99);
    }
}
