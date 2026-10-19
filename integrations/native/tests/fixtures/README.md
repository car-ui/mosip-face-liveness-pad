# Native fixtures

`portrait-face.iso` contains the NASA astronaut fixture from `tests/sample_images/astronaut.png`, JPEG-encoded for ISO/IEC 19794-5:2011 interoperability tests. The source image attribution and source checksum are in `tests/sample_images/README.md`.

The reference SBI's NprUtils `BioFace.generateFaceISO2011` encoder created this record. An independent MOSIP `FaceBDIR` parser verified the JPEG image-type tag and exact embedded JPEG bytes. It is a static photograph, with no live action or presentation-attack evidence. Tests that attach completed action metadata to it explicitly simulate that metadata.

`blank-face.iso` is the older synthetic rejection fixture. Its upstream convenience encoder labels its JPEG bytes as JPEG2000. It exercises existing decoding rejection paths and does not establish ISO conformance. Use the portrait fixture for exact JPEG binding tests.

`dimensions-gradient.jp2` and `dimensions-gradient.j2k` are generated RGB ramps,
64 by 48 pixels, with no faces or camera data. Pillow 13 encoded the same pixels
losslessly as a boxed JP2 and a raw JPEG2000 codestream. The pixel at `(x,y)` is
`(4*x, 5*y, 2*(x+y))`. Both were decoded and compared with the source pixels.
They exercise dimension checks and decoder compatibility, not PAD accuracy.

SHA-256:

- JP2: `dfa5b1876c8ac3dae3ff3dc45425bfbc56f103d2d772ae7bd225f225fca3f96a`
- J2K: `a18775bb5321066485b545df00b0455b3b4ecf0147264799671874b5f27d6a68`
