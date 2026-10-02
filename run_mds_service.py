"""
Entry point to launch the MOSIP Device Service (MDS) Server on port 4501
"""

import uvicorn
from src.mds.mds_server import app


def main():
    print("=" * 60)
    print("Starting MOSIP Device Service (MDS) L0/L1 Server...")
    print("API Specification : MOSIP Device Service 0.9.5 / 1.2.0")
    print("Device Discovery  : http://127.0.0.1:4501/info")
    print("Video Stream      : http://127.0.0.1:4501/stream")
    print("Biometric Capture : http://127.0.0.1:4501/capture")
    print("Web Console       : http://127.0.0.1:4501/")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=4501)


if __name__ == "__main__":
    main()
