"""
Standard Physical Webcam Implementation (L0 Device)
Captures live frames from built-in or USB cameras via OpenCV/UVC abstraction.
Conforms to FaceCaptureDevice interface.
"""

import time
import cv2
from typing import Optional, Generator, Tuple
from .base import FaceCaptureDevice, DeviceInfo, DeviceType, DeviceStatus, VideoFrame


class WebcamCaptureDevice(FaceCaptureDevice):
    def __init__(self, camera_index: int = 0, target_width: int = 640, target_height: int = 480):
        self.camera_index = camera_index
        self.target_width = target_width
        self.target_height = target_height
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_streaming = False
        self._frame_count = 0
        self._info = DeviceInfo(
            device_id=f"WEBCAM_L0_{camera_index}",
            device_name=f"Standard Integrated/USB Camera #{camera_index}",
            device_type=DeviceType.PHYSICAL_L0_WEBCAM,
            serial_number=f"CAM-SN-{camera_index:04d}",
            firmware_version="1.0.0",
            is_l1_secure=False,
            status=DeviceStatus.DISCONNECTED
        )

    def connect(self) -> bool:
        try:
            # Try DirectShow on Windows for fast startup, then fallback
            self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self._cap.isOpened():
                self._cap = cv2.VideoCapture(self.camera_index)
            
            if self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
                self._cap.set(cv2.CAP_PROP_FPS, 30)
                self._info.status = DeviceStatus.CONNECTED
                return True
            else:
                self._info.status = DeviceStatus.ERROR
                return False
        except Exception:
            self._info.status = DeviceStatus.ERROR
            return False

    def disconnect(self) -> None:
        self.stop_stream()
        if self._cap and self._cap.isOpened():
            self._cap.release()
        self._cap = None
        self._info.status = DeviceStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def is_available(self) -> bool:
        if self.is_connected():
            return True
        try:
            temp_cap = cv2.VideoCapture(self.camera_index)
            avail = temp_cap.isOpened()
            temp_cap.release()
            return avail
        except Exception:
            return False

    def get_device_info(self) -> DeviceInfo:
        return self._info

    def read_frame(self) -> Tuple[bool, Optional[VideoFrame]]:
        if not self.is_connected():
            return False, None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return False, None

        self._frame_count += 1
        h, w = frame.shape[:2]
        video_frame = VideoFrame(
            frame_id=self._frame_count,
            timestamp_ms=time.time() * 1000.0,
            image=frame,
            width=w,
            height=h,
            is_key_frame=(self._frame_count % 30 == 0)
        )
        return True, video_frame

    def start_stream(self) -> Generator[VideoFrame, None, None]:
        if not self.is_connected():
            if not self.connect():
                raise RuntimeError("Failed to connect to webcam device.")

        self._is_streaming = True
        self._info.status = DeviceStatus.STREAMING
        while self._is_streaming and self.is_connected():
            success, frame = self.read_frame()
            if success and frame is not None:
                yield frame
            else:
                time.sleep(0.01)

    def stop_stream(self) -> None:
        self._is_streaming = False
        if self.is_connected():
            self._info.status = DeviceStatus.CONNECTED
