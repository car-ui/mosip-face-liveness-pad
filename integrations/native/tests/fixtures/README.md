# Native fixtures

`portrait-face.iso` contains the NASA astronaut fixture from `tests/sample_images/astronaut.png`, JPEG-encoded for ISO/IEC 19794-5:2011 interoperability tests. The source image attribution and source checksum are in `tests/sample_images/README.md`.

The reference SBI's NprUtils `BioFace.generateFaceISO2011` encoder created this record. An independent MOSIP `FaceBDIR` parser verified the JPEG image-type tag and exact embedded JPEG bytes. It is a static photograph, with no live action or presentation-attack evidence. Tests that attach completed action metadata to it explicitly simulate that metadata.

`blank-face.iso` is the older synthetic rejection fixture. Its upstream convenience encoder labels its JPEG bytes as JPEG2000. It exercises existing decoding rejection paths and does not establish ISO conformance. Use the portrait fixture for exact JPEG binding tests.
