package io.mosip.facepad;

import java.security.SecureRandom;
import java.util.concurrent.atomic.AtomicLong;

/** Injected landmark geometry tests control flow, not camera/action model accuracy. */
public final class NativeActiveSessionCheck {
    private static final byte[] JPEG = {(byte)255,(byte)216,1,2,(byte)255,(byte)217};
    private static final NativePadEngine.Decision CLEAR = new NativePadEngine.Decision(true,"PASSIVE_CLEAR",.99);
    private static final class Fixture {
        final AtomicLong clock = new AtomicLong();
        final NativeActiveSession session = new NativeActiveSession(10000, clock::get, new SecureRandom() {
            public boolean nextBoolean() { return true; }
        });
        long sequence;
        byte[] candidate = JPEG;
        void frame(double ear, double turn) throws Exception {
            clock.addAndGet(100_000_000L);
            session.observe(++sequence, geometry(ear,turn),CLEAR,candidate);
        }
        void neutral(int n) throws Exception { for (int i=0;i<n;i++) frame(.3,0); }
        void complete() throws Exception {
            neutral(3);
            for(int i=0;i<3;i++) frame(.1,0);
            neutral(2);
            neutral(3);
            for(int i=0;i<3;i++) frame(.3,-.4);
            neutral(2);
        }
    }
    private static NativeLandmarkEngine.Observation geometry(double ear, double turn) throws Exception {
        float[] points = new float[478*3];
        int[][] eyes={{33,160,158,133,153,144},{362,385,387,263,373,380}};
        for(int i=0;i<2;i++) {
            int[] ids=eyes[i]; double x=i==0?80:156, height=ear*20;
            double[][] xy={{x,100},{x+5,100-height/2},{x+15,100-height/2},{x+20,100},
                    {x+15,100+height/2},{x+5,100+height/2}};
            for(int j=0;j<6;j++) {points[ids[j]*3]=(float)xy[j][0];points[ids[j]*3+1]=(float)xy[j][1];}
        }
        points[3]=(float)(128+turn*48);points[4]=120;
        return new NativeLandmarkEngine.Observation(points,.99);
    }
    private static void require(boolean condition,String message) {
        if(!condition) throw new AssertionError(message);
    }
    /** Explicit geometry double for upstream controller acceptance-path checks only. */
    public static NativeActiveSession completedForControllerTest(byte[] exactFrame) throws Exception {
        Fixture fixture = new Fixture(); fixture.candidate = exactFrame; fixture.complete();
        require(fixture.session.state() == NativeActiveSession.State.COMPLETE, "Fixture did not complete");
        return fixture.session;
    }
    public static void main(String[] args) throws Exception {
        Fixture accepted=new Fixture();accepted.complete();
        require(accepted.session.state()==NativeActiveSession.State.COMPLETE,"Action sequence did not complete");
        require(accepted.session.consume(JPEG),"Exact frame was not consumable");
        require(!accepted.session.consume(JPEG),"Evidence reused");
        Fixture wrong=new Fixture();wrong.complete();
        require(!wrong.session.consume(new byte[]{1,2,3}),"Different final candidate accepted");
        Fixture staticPhoto=new Fixture();staticPhoto.neutral(40);
        require(staticPhoto.session.state()==NativeActiveSession.State.VERIFYING,"Static face completed actions");
        Fixture closed=new Fixture();for(int i=0;i<20;i++)closed.frame(.1,0);
        require(closed.session.prompt().startsWith("Look straight"),"Closed-eye start armed challenge");
        Fixture loss=new Fixture();loss.neutral(3);loss.frame(.1,0);loss.session.invalidateFrame();loss.neutral(2);
        require(loss.session.prompt().startsWith("Look straight"),"Face loss retained challenge progression");
        Fixture duplicate=new Fixture();duplicate.neutral(1);
        duplicate.session.observe(duplicate.sequence,geometry(.3,0),CLEAR,JPEG);
        require(duplicate.session.state()==NativeActiveSession.State.REJECTED,"Duplicate frame accepted");
        Fixture attack=new Fixture();attack.neutral(3);
        attack.session.observe(++attack.sequence,geometry(.1,0),new NativePadEngine.Decision(false,"PRESENTATION_ATTACK",.01),JPEG);
        require(attack.session.state()==NativeActiveSession.State.REJECTED,"Action overrode attack");
        Fixture expired=new Fixture();expired.complete();expired.clock.set(11_000_000_000L);
        require(!expired.session.consume(JPEG),"Expired completion accepted");
        Fixture stale=new Fixture();stale.complete();stale.clock.addAndGet(3_000_000_000L);
        require(!stale.session.consume(JPEG),"Completion older than two seconds accepted");
        Fixture cancelled=new Fixture();cancelled.complete();cancelled.session.cancel();
        require(!cancelled.session.consume(JPEG),"Cancelled stream proof accepted");
        Fixture gap=new Fixture();gap.neutral(3);gap.clock.addAndGet(2_000_000_000L);gap.frame(.1,0);
        require(gap.session.prompt().startsWith("Look straight"),"Stream gap preserved action phase");
        System.out.println("PASS native action control flow: neutral baseline, blink/turn/return, static rejection, face loss, sequence, PAD failure, expiry and one-use exact-frame binding");
        System.out.println("Evidence scope: injected landmark geometry; no live action, physical attack or real identity-matching claim");
    }
}
