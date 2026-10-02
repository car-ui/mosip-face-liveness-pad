"""
Mock L0/L1 Biometric Device Simulator
Allows automated testing, CI/CD, and simulated spoof attack evaluation.
Supports video replay, synthetic live faces, and presentation attack scenarios.
"""

import time
import cv2
import numpy as np
from typing import Optional, Generator, Tuple
from .base import FaceCaptureDevice, DeviceInfo, DeviceType, DeviceStatus, VideoFrame


class MockL0Device(FaceCaptureDevice):
    def __init__(self, video_source: Optional[str] = None, loop: bool = True, fps: int = 30):
        self.video_source = video_source
        self.loop = loop
        self.fps = fps
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_streaming = False
        self._frame_count = 0
        self._info = DeviceInfo(
            device_id="MOCK_L0_SIM_001",
            device_name="MOSIP Mock L0/L1 Biometric Device Simulator",
            device_type=DeviceType.MOCK_L0_SIMULATOR,
            serial_number="MOCK-MDS-9999",
            firmware_version="2.4.0-sim",
            is_l1_secure=True,
            status=DeviceStatus.DISCONNECTED
        )

    def connect(self) -> bool:
        if self.video_source:
            self._cap = cv2.VideoCapture(self.video_source)
            if not self._cap.isOpened():
                # If file not found, we can fall back to synthetic frame generator
                self._cap = None
        self._info.status = DeviceStatus.CONNECTED
        return True

    def disconnect(self) -> None:
        self.stop_stream()
        if self._cap:
            self._cap.release()
            self._cap = None
        self._info.status = DeviceStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._info.status in (DeviceStatus.CONNECTED, DeviceStatus.STREAMING)

    def get_device_info(self) -> DeviceInfo:
        return self._info

    def _generate_synthetic_frame(self) -> np.ndarray:
        """
        Generates a synthetic test frame with an animated face-like pattern
        if no video file is provided.
        """
        frame = np.full((480, 640, 3), 40, dtype=np.uint8)
        
        # Draw background grid
        for y in range(0, 480, 40):
            cv2.line(frame, (0, y), (640, y), (50, 50, 50), 1)
        for x in range(0, 640, 40):
            cv2.line(frame, (x, 0), (x, 480), (50, 50, 50), 1)

        # Draw a synthetic face structure
        center_x, center_y = 320, 240
        # Head oval
        cv2.ellipse(frame, (center_x, center_y), (110, 150), 0, 0, 360, (180, 200, 230), -1)
        cv2.ellipse(frame, (center_x, center_y), (110, 150), 0, 0, 360, (100, 120, 150), 3)

        # Eyes (simulate periodic blink)
        blink = (self._frame_count // 30) % 4 == 0
        eye_y = center_y - 25
        if blink:
            cv2.line(frame, (center_x - 45, eye_y), (center_x - 20, eye_y), (30, 30, 30), 3)
            cv2.line(frame, (center_x + 20, eye_y), (center_x + 45, eye_y), (30, 30, 30), 3)
        else:
            cv2.circle(frame, (center_x - 35, eye_y), 12, (255, 255, 255), -1)
            cv2.circle(frame, (center_x - 35, eye_y), 5, (20, 20, 20), -1)
            cv2.circle(frame, (center_x + 35, eye_y), 12, (255, 255, 255), -1)
            cv2.circle(frame, (center_x + 35, eye_y), 5, (20, 20, 20), -1)

        # Nose
        cv2.line(frame, (center_x, eye_y + 10), (center_x, center_y + 20), (120, 130, 160), 3)

        # Mouth (simulate smile on cycle)
        smile = (self._frame_count // 45) % 2 == 1
        mouth_y = center_y + 65
        if smile:
            cv2.ellipse(frame, (center_x, mouth_y), (30, 15), 0, 0, 180, (40, 40, 180), 3)
        else:
            cv2.line(frame, (center_x - 25, mouth_y), (center_x + 25, mouth_y), (40, 40, 180), 3)

        # Telemetry watermark
        cv2.putText(frame, f"MOCK L0/L1 STREAM - Frame {self._frame_count}", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 200), 2)
        cv2.putText(frame, "MOSIP Device Simulator", (20, 455),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        return frame

    def read_frame(self) -> Tuple[bool, Optional[VideoFrame]]:
        if not self.is_connected():
            return False, None

        frame = None
        if self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if not ret or frame is None:
                if self.loop:
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self._cap.read()
                else:
                    return False, None

        if frame is None:
            # Fall back to synthetic pattern
            frame = self._generate_synthetic_frame()

        self._frame_count += 1
        h, w = frame.shape[:2]
        video_frame = VideoFrame(
            frame_id=self._frame_count,
            timestamp_ms=time.time() * 1000.0,
            image=frame,
            width=w,
            height=h,
            is_key_frame=(self._frame_count % 30 == 0),
            metadata={"device": "MOCK_L0_SIMULATOR"}
        )
        return True, video_frame

    def start_stream(self) -> Generator[VideoFrame, None, None]:
        if not self.is_connected():
            self.connect()

        self._is_streaming = True
        self._info.status = DeviceStatus.STREAMING
        interval = 1.0 / self.fps
        while self._is_streaming:
            t0 = time.time()
            success, frame = self.read_frame()
            if success and frame is not None:
                yield frame
            elapsed = time.time() - t0
            sleep_time = max(0.001, interval - elapsed)
            time.sleep(sleep_time)

    def stop_stream(self) -> None:
        self._is_streaming = False
        if self.is_connected():
            self._info.status = DeviceStatus.CONNECTED
