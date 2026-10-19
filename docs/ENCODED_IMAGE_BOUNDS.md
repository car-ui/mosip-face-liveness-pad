# Native image preflight

Encoded byte count does not bound decoded image size. Native frame and capture
paths now check dimensions before allocating a decoder image. The camera-owned
active path requires JPEG. Final-image checks also recognize PNG, boxed JP2 and
raw JPEG2000 codestreams.

JPEG2000 field order and consistency checks were researched against the
[OpenJPEG 2.5.3 codestream reader](https://github.com/uclouvain/openjpeg/blob/v2.5.3/src/lib/openjp2/j2k.c)
and [JP2 header reader](https://github.com/uclouvain/openjpeg/blob/v2.5.3/src/lib/openjp2/jp2.c).
The guard checks both container dimensions and codestream dimensions; accepting
only the container declaration would leave the allocation size unbounded.

The guard accepts at most 8 MiB of encoded data and 4096 pixels per side.
JPEG supports eight-bit baseline, extended sequential and progressive headers.
JPEG2000 also bounds reference-canvas and tile dimensions, tile count to 4096,
components to one, three or four, precision to 16 bits, and component sampling.
Extended JP2 lengths must fit in the supplied byte array. Conflicting headers,
duplicate codestreams and unsupported variants reject. These are engineering
limits; physical vendor compatibility with every supported format is unverified.

This is a dimension preflight, not a replacement codec, image-integrity proof or
general decoder-security guarantee. The existing decoder must still accept the
pixels. The downstream PAD gate still requires one face, the model contract and
any required active proof. JPEG2000 final images cannot consume the desktop's
JPEG-bound active proof.

The pure Java check exercises real PNG, JP2 and J2K fixtures, JPEG headers,
truncation, oversized images and tile grids, extended box lengths, conflicting
dimensions and 2000 malformed inputs. The synthetic gradients contain no people.
Native ONNX checks separately verify that supported JPEG2000 fixtures decode and
that undersized images cannot produce an accepted capture.
