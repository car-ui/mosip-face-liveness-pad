package io.mosip.facepad;

import java.io.IOException;

/** Checks encoded dimensions before allocating decoder images. This does not validate image pixels. */
public final class BoundedImage {
    private static final int MAX_BYTES = 8 * 1024 * 1024, MAX_SIDE = 4096, MAX_JPEG_HEADER = 1024 * 1024;
    private BoundedImage() { }

    public static int[] requireImage(byte[] bytes) throws IOException {
        size(bytes);
        if (u8(bytes,0) == 255 && u8(bytes,1) == 216) return requireJpeg(bytes);
        if (u16(bytes,0) == 0xff4f) return imageSize(j2k(bytes,0,bytes.length));
        if (bytes.length >= 12 && u32(bytes,0) == 12 && u32(bytes,4) == 0x6a502020L
                && u32(bytes,8) == 0x0d0a870aL) return jp2(bytes);
        int[] signature = {137,80,78,71,13,10,26,10};
        if (bytes.length < 33) throw new IOException("Unsupported image header");
        for (int i=0;i<signature.length;i++) if (u8(bytes,i) != signature[i])
            throw new IOException("Unsupported image format");
        if (u32(bytes,8) != 13 || u32(bytes,12) != 0x49484452L)
            throw new IOException("Invalid PNG dimensions header");
        return dimensions(u32(bytes,16),u32(bytes,20));
    }

    private static int[] jp2(byte[] bytes) throws IOException {
        int position=12,count=0;
        int[] declared=null,codestream=null;
        while(position < bytes.length) {
            if(++count>256)throw new IOException("Too many JP2 boxes");
            int[] box=box(bytes,position,bytes.length);
            long type=u32(bytes,position+4);
            if(type==0x6a703268L) {
                if(declared!=null)throw new IOException("Duplicate JP2 header");
                int child=box[0],children=0;
                while(child<box[1]) {
                    if(++children>128)throw new IOException("Too many JP2 header boxes");
                    int[] inner=box(bytes,child,box[1]);
                    if(u32(bytes,child+4)==0x69686472L) {
                        if(declared!=null || inner[1]-inner[0]!=14)throw new IOException("Invalid JP2 image header");
                        int[] shape=dimensions(u32(bytes,inner[0]+4),u32(bytes,inner[0]));
                        int components=u16(bytes,inner[0]+8),precision=u8(bytes,inner[0]+10);
                        if((components!=1 && components!=3 && components!=4)
                                || (precision!=255 && (precision&127)>15) || u8(bytes,inner[0]+11)!=7)
                            throw new IOException("Unsupported JP2 components");
                        declared=new int[]{shape[0],shape[1],components};
                    }
                    child=inner[1];
                }
                if(declared==null)throw new IOException("JP2 image header missing");
            } else if(type==0x6a703263L) {
                if(codestream!=null)throw new IOException("Multiple JP2 codestreams unsupported");
                codestream=j2k(bytes,box[0],box[1]);
            }
            position=box[1];
        }
        if(declared==null || codestream==null || !java.util.Arrays.equals(declared,codestream))
            throw new IOException("JP2 image and codestream dimensions disagree");
        return imageSize(codestream);
    }

    /** Box payload start and end. Extended lengths must fit inside the bounded byte array. */
    private static int[] box(byte[] bytes,int position,int limit) throws IOException {
        if(limit-position<8)throw new IOException("Truncated JP2 box");
        long length=u32(bytes,position);int header=8;
        if(length==1) {
            if(limit-position<16 || u32(bytes,position+8)!=0)throw new IOException("JP2 extended length outside bounds");
            length=u32(bytes,position+12);header=16;
        } else if(length==0)length=limit-position;
        if(length<header || length>limit-position)throw new IOException("JP2 box outside bounds");
        return new int[]{position+header,position+(int)length};
    }

    private static int[] j2k(byte[] bytes,int start,int end) throws IOException {
        if(end-start<45 || u16(bytes,start)!=0xff4f || u16(bytes,start+2)!=0xff51
                || u16(bytes,end-2)!=0xffd9)throw new IOException("Invalid JPEG2000 codestream header");
        int length=u16(bytes,start+4),components=u16(bytes,start+40);
        if((components!=1 && components!=3 && components!=4) || length!=38+3*components || length>end-start-4)
            throw new IOException("Invalid JPEG2000 size marker");
        long right=u32(bytes,start+8),bottom=u32(bytes,start+12),left=u32(bytes,start+16),top=u32(bytes,start+20);
        dimensions(right,bottom);
        int[] shape=dimensions(right-left,bottom-top);
        long tileWidth=u32(bytes,start+24),tileHeight=u32(bytes,start+28);
        long tileLeft=u32(bytes,start+32),tileTop=u32(bytes,start+36);
        dimensions(tileWidth,tileHeight);
        if(tileLeft>left || tileTop>top || tileLeft+tileWidth<=left || tileTop+tileHeight<=top
                || ((right-tileLeft+tileWidth-1)/tileWidth)*((bottom-tileTop+tileHeight-1)/tileHeight)>4096)
            throw new IOException("JPEG2000 tile grid outside bounds");
        for(int i=0;i<components;i++) {
            int offset=start+42+i*3;
            if((u8(bytes,offset)&127)>15 || u8(bytes,offset+1)<1 || u8(bytes,offset+1)>16
                    || u8(bytes,offset+2)<1 || u8(bytes,offset+2)>16)
                throw new IOException("Unsupported JPEG2000 component sampling");
        }
        return new int[]{shape[0],shape[1],components};
    }

    private static int[] imageSize(int[] header) { return new int[]{header[0],header[1]}; }

    public static int[] requireJpeg(byte[] bytes) throws IOException {
        size(bytes);
        if (u8(bytes,0) != 255 || u8(bytes,1) != 216 || u8(bytes,bytes.length-2) != 255
                || u8(bytes,bytes.length-1) != 217) throw new IOException("Invalid JPEG markers");
        int position=2;
        while (position < Math.min(bytes.length,MAX_JPEG_HEADER)) {
            if (u8(bytes,position++) != 255) throw new IOException("Invalid JPEG marker");
            while (position < bytes.length && u8(bytes,position) == 255) position++;
            if (position >= bytes.length) throw new IOException("Truncated JPEG marker");
            int marker=u8(bytes,position++);
            if (marker == 1) continue;
            if (marker == 0 || marker == 216 || marker == 217 || marker == 218 || (marker >= 208 && marker <= 215))
                throw new IOException("JPEG frame dimensions unavailable");
            if (position+2 > bytes.length) throw new IOException("Truncated JPEG segment");
            int length=u16(bytes,position);
            if (length < 2 || length > bytes.length-position || position+length > MAX_JPEG_HEADER)
                throw new IOException("JPEG header segment outside bounds");
            if (marker == 192 || marker == 193 || marker == 194) {
                if (length < 11 || u8(bytes,position+2) != 8) throw new IOException("Unsupported JPEG frame");
                int components=u8(bytes,position+7);
                if ((components != 1 && components != 3 && components != 4) || length != 8+3*components)
                    throw new IOException("Invalid JPEG component header");
                return dimensions(u16(bytes,position+5),u16(bytes,position+3));
            }
            // Other frame coding types cannot be treated as harmless metadata.
            if (marker >= 192 && marker <= 207 && marker != 196 && marker != 200 && marker != 204)
                throw new IOException("Unsupported JPEG frame coding");
            position+=length;
        }
        throw new IOException("JPEG frame header exceeds bounds");
    }

    private static void size(byte[] bytes) throws IOException {
        if (bytes == null || bytes.length < 4 || bytes.length > MAX_BYTES)
            throw new IOException("Encoded image size outside bounds");
    }
    private static int[] dimensions(long width,long height) throws IOException {
        if (width < 1 || height < 1 || width > MAX_SIDE || height > MAX_SIDE)
            throw new IOException("Image dimensions outside bounds");
        return new int[]{(int)width,(int)height};
    }
    private static int u8(byte[] bytes,int offset) { return bytes[offset] & 255; }
    private static int u16(byte[] bytes,int offset) { return (u8(bytes,offset)<<8)|u8(bytes,offset+1); }
    private static long u32(byte[] bytes,int offset) {
        return ((long)u8(bytes,offset)<<24)|((long)u8(bytes,offset+1)<<16)|((long)u8(bytes,offset+2)<<8)|u8(bytes,offset+3);
    }
}
