import io.mosip.facepad.BoundedImage;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;

/** Header checks only. Real pixel decoding remains the model bridge's responsibility. */
public final class BoundedImageCheck {
    private static byte[] jpeg(int width,int height,int coding) {
        return new byte[]{(byte)255,(byte)216,(byte)255,(byte)coding,0,11,8,
            (byte)(height>>8),(byte)height,(byte)(width>>8),(byte)width,1,1,17,0,(byte)255,(byte)217};
    }
    private static void reject(byte[] bytes) throws Exception {
        try { BoundedImage.requireImage(bytes);throw new AssertionError("Invalid image header accepted"); }
        catch(IOException expected) { }
    }
    private static void put32(byte[] bytes,int offset,int value) {
        for(int i=0;i<4;i++)bytes[offset+i]=(byte)(value>>(24-i*8));
    }
    private static int marker(byte[] bytes,String text) throws Exception {
        byte[] target=text.getBytes("US-ASCII");
        for(int i=0;i<=bytes.length-target.length;i++) {
            boolean same=true;for(int j=0;j<target.length;j++)same &= bytes[i+j]==target[j];
            if(same)return i;
        }
        throw new AssertionError("Fixture marker missing");
    }
    public static void main(String[] args) throws Exception {
        for(int coding:new int[]{192,193,194}) {
            int[] dimensions=BoundedImage.requireJpeg(jpeg(640,480,coding));
            if(dimensions[0]!=640 || dimensions[1]!=480)throw new AssertionError("Wrong JPEG dimensions");
        }
        reject(null);reject(new byte[0]);reject(jpeg(0,480,192));reject(jpeg(65535,65535,192));
        reject(jpeg(640,480,195));
        byte[] frame=jpeg(640,480,192);
        for(int n=0;n<frame.length;n++)reject(Arrays.copyOf(frame,n));
        byte[] bad=frame.clone();bad[5]=1;reject(bad);
        bad=frame.clone();bad[5]=(byte)255;reject(bad);
        bad=frame.clone();bad[11]=3;reject(bad);
        byte[] png=Files.readAllBytes(Paths.get(args[0]));
        int[] dimensions=BoundedImage.requireImage(png);
        if(dimensions[0]!=512 || dimensions[1]!=512)throw new AssertionError("Wrong PNG dimensions");
        png[16]=(byte)255;reject(png);
        Path root=Paths.get(args[0]).toAbsolutePath().getParent().getParent().getParent();
        byte[] jp2=Files.readAllBytes(root.resolve("integrations/native/tests/fixtures/dimensions-gradient.jp2"));
        byte[] raw=Files.readAllBytes(root.resolve("integrations/native/tests/fixtures/dimensions-gradient.j2k"));
        for(byte[] fixture:new byte[][]{jp2,raw}) {
            if(!Arrays.equals(BoundedImage.requireImage(fixture),new int[]{64,48}))throw new AssertionError("Wrong JPEG2000 dimensions");
            for(int n=0;n<fixture.length;n++)reject(Arrays.copyOf(fixture,n));
        }
        bad=jp2.clone();int ihdr=marker(bad,"ihdr");put32(bad,ihdr+8,65);reject(bad);
        bad=raw.clone();put32(bad,8,65535);reject(bad);
        bad=raw.clone();put32(bad,8,4096);put32(bad,12,4096);put32(bad,24,1);put32(bad,28,1);reject(bad);
        int boxStart=marker(jp2,"jp2c")-4;
        byte[] extended=new byte[jp2.length+8];
        System.arraycopy(jp2,0,extended,0,boxStart);put32(extended,boxStart,1);
        System.arraycopy(jp2,boxStart+4,extended,boxStart+4,4);
        put32(extended,boxStart+12,jp2.length-boxStart+8);
        System.arraycopy(jp2,boxStart+8,extended,boxStart+16,jp2.length-boxStart-8);
        if(!Arrays.equals(BoundedImage.requireImage(extended),new int[]{64,48}))throw new AssertionError("Valid extended JP2 box rejected");
        extended[boxStart+8]=1;reject(extended);
        Random random=new Random(19);
        for(int i=0;i<2000;i++) {
            byte[] fuzz=new byte[random.nextInt(128)];random.nextBytes(fuzz);
            if(fuzz.length>=12) {
                if(i%3==0) {fuzz[0]=(byte)255;fuzz[1]=(byte)216;fuzz[fuzz.length-2]=(byte)255;fuzz[fuzz.length-1]=(byte)217;}
                if(i%3==1)System.arraycopy(jp2,0,fuzz,0,12);
                if(i%3==2) {fuzz[0]=(byte)255;fuzz[1]=79;fuzz[2]=(byte)255;fuzz[3]=81;}
            }
            try {
                int[] shape=BoundedImage.requireImage(fuzz);
                if(shape[0]<1 || shape[1]<1 || shape[0]>4096 || shape[1]>4096)throw new AssertionError("Unbounded fuzz dimensions");
            } catch(IOException expected) { }
        }
        System.out.println("PASS bounded JPEG/PNG/JP2/J2K headers: real lossless fixtures, extended boxes, conflicting dimensions, oversized tile grids, truncation and 2000 malformed inputs");
    }
}
