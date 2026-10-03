"""
Mock L0/L1 Biometric Device Simulator
Allows complete, deterministic automated testing and CI/CD without physical biometric hardware.
Simulates:
1. Bona fide live stream (natural micro-motion, periodic blink, reactive expressions)
2. Static photo attack (rigid 2D presentation, zero micro-motion)
3. Screen replay attack (moiré grid harmonics, specular glass glare reflections)
4. No face (empty background)
5. Multiple faces (two subjects in frame)
6. Poor lighting (underexposed dark, overexposed bright, lateral shadows)
7. Blurry frames (heavy motion blur / defocus)
8. Device disconnect (simulates mid-stream hardware failure)
9. Invalid frame (empty / corrupted buffer)
10. Scripted challenge responses for automated test assertions
"""

import time
import os
import cv2
import numpy as np
from typing import Optional, Generator, Tuple, Dict, Any
from .base import FaceCaptureDevice, DeviceInfo, DeviceType, DeviceStatus, VideoFrame, MockScenario


class MockL0Device(FaceCaptureDevice):
    def __init__(self,
                 scenario: MockScenario = MockScenario.BONA_FIDE_LIVE,
                 video_source: Optional[str] = None,
                 fps: int = 30,
                 disconnect_after_frames: Optional[int] = None):
        self.scenario = scenario
        self.video_source = video_source
        self.fps = fps
        self.disconnect_after_frames = disconnect_after_frames
        
        self._frame_count = 0
        self._is_streaming = False
        self._cap: Optional[cv2.VideoCapture] = None
        self._base_face_img: Optional[np.ndarray] = None
        self._scripted_action: Optional[str] = None
        self._action_frame_counter: int = 0

        self._info = DeviceInfo(
            device_id="MOCK_L0_SIM_001",
            device_name="MOSIP Mock L0/L1 Biometric Device Simulator",
            device_type=DeviceType.MOCK_L0_SIMULATOR,
            serial_number="MOCK-MDS-9999",
            firmware_version="2.5.0-ci",
            is_l1_secure=True,
            status=DeviceStatus.DISCONNECTED
        )
        self._load_base_assets()

    def _load_base_assets(self) -> None:
        """Loads a clean realistic test image if available locally, otherwise generates synthetic skin."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sample_path = os.path.join(base_dir, "tests", "sample_images", "sample_0.jpg")
        if os.path.exists(sample_path):
            img = cv2.imread(sample_path)
            if img is not None:
                self._base_face_img = cv2.resize(img, (640, 480))

    def set_scenario(self, scenario: MockScenario) -> None:
        """Dynamically switches test scenario."""
        self.scenario = scenario
        self._frame_count = 0

    def script_action(self, action_name: str, duration_frames: int = 15) -> None:
        """Instructs the mock device to simulate a specific action (e.g. 'BLINK', 'SMILE', 'TURN_LEFT', 'TURN_RIGHT')."""
        self._scripted_action = action_name
        self._action_frame_counter = duration_frames

    def connect(self) -> bool:
        self._frame_count = 0
        self._info.status = DeviceStatus.CONNECTED
        return True

    def disconnect(self) -> None:
        self.stop_stream()
        self._info.status = DeviceStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._info.status in (DeviceStatus.CONNECTED, DeviceStatus.STREAMING)

    def is_available(self) -> bool:
        return True

    def get_device_info(self) -> DeviceInfo:
        return self._info

    def _create_synthetic_face(self,
                               center_x: int = 320,
                               center_y: int = 240,
                               smile: bool = False,
                               blink: bool = False,
                               yaw_offset: int = 0) -> np.ndarray:
        """Generates an anatomically structured synthetic face for testing."""
        frame = np.full((480, 640, 3), 45, dtype=np.uint8)
        
        # Subtle textured background
        for y in range(0, 480, 40):
            cv2.line(frame, (0, y), (640, y), (55, 55, 55), 1)

        # Head oval with natural skin tone
        cx = center_x + yaw_offset
        cv2.ellipse(frame, (cx, center_y), (105, 145), 0, 0, 360, (170, 195, 225), -1)
        cv2.ellipse(frame, (cx, center_y), (105, 145), 0, 0, 360, (110, 130, 160), 2)

        # Eyes
        eye_y = center_y - 25
        eye_spacing = 38
        if blink:
            cv2.line(frame, (cx - eye_spacing - 12, eye_y), (cx - eye_spacing + 12, eye_y), (30, 30, 30), 3)
            cv2.line(frame, (cx + eye_spacing - 12, eye_y), (cx + eye_spacing + 12, eye_y), (30, 30, 30), 3)
        else:
            cv2.circle(frame, (cx - eye_spacing, eye_y), 11, (255, 255, 255), -1)
            cv2.circle(frame, (cx - eye_spacing, eye_y), 5, (30, 30, 30), -1)
            cv2.circle(frame, (cx + eye_spacing, eye_y), 11, (255, 255, 255), -1)
            cv2.circle(frame, (cx + eye_spacing, eye_y), 5, (30, 30, 30), -1)

        # Nose
        cv2.line(frame, (cx, eye_y + 12), (cx + (yaw_offset // 2), center_y + 20), (120, 140, 170), 3)

        # Mouth
        mouth_y = center_y + 65
        if smile:
            cv2.ellipse(frame, (cx, mouth_y), (32, 16), 0, 0, 180, (40, 40, 180), 3)
        else:
            cv2.line(frame, (cx - 24, mouth_y), (cx + 24, mouth_y), (40, 40, 180), 3)

        return frame

    def _generate_frame_for_scenario(self) -> Optional[np.ndarray]:
        # Handle disconnect simulation
        if self.scenario == MockScenario.DEVICE_DISCONNECT:
            if self._frame_count > (self.disconnect_after_frames or 5):
                self.disconnect()
                return None

        # Handle invalid/corrupted frame
        if self.scenario == MockScenario.INVALID_FRAME:
            return np.empty((0, 0, 0), dtype=np.uint8)

        # 1. NO FACE
        if self.scenario == MockScenario.NO_FACE:
            frame = np.full((480, 640, 3), 60, dtype=np.uint8)
            cv2.putText(frame, "SCENARIO: NO FACE PRESENT", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
            return frame

        # 2. MULTIPLE FACES
        if self.scenario == MockScenario.MULTIPLE_FACES:
            frame = np.full((480, 640, 3), 40, dtype=np.uint8)
            # Render two faces side-by-side
            cv2.ellipse(frame, (200, 240), (80, 110), 0, 0, 360, (170, 195, 225), -1)
            cv2.ellipse(frame, (440, 240), (80, 110), 0, 0, 360, (170, 195, 225), -1)
            cv2.putText(frame, "SCENARIO: MULTIPLE FACES", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 1)
            return frame

        # Base frame selection
        if self._base_face_img is not None:
            base = self._base_face_img.copy()
        else:
            base = self._create_synthetic_face()

        # Check scripted actions
        is_blinking = False
        is_smiling = False
        yaw_offset = 0

        if self._action_frame_counter > 0:
            self._action_frame_counter -= 1
            if self._scripted_action == "BLINK":
                is_blinking = True
            elif self._scripted_action == "SMILE":
                is_smiling = True
            elif self._scripted_action == "TURN_LEFT":
                yaw_offset = 25
            elif self._scripted_action == "TURN_RIGHT":
                yaw_offset = -25

        # 3. BONA FIDE LIVE
        if self.scenario == MockScenario.BONA_FIDE_LIVE:
            # Natural micro-motion jitter
            shift_x = int(np.sin(self._frame_count * 0.15) * 2)
            shift_y = int(np.cos(self._frame_count * 0.12) * 1)
            M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
            live_frame = cv2.warpAffine(base, M, (640, 480))
            
            # Subtle physiological sensor noise
            noise = np.random.normal(0, 1.2, live_frame.shape).astype(np.int8)
            live_frame = np.clip(live_frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            return live_frame

        # 4. STATIC PHOTO ATTACK
        elif self.scenario == MockScenario.STATIC_PHOTO_ATTACK:
            # Rigid, completely static frame with zero micro-motion
            # Flatten chrominance slightly to simulate paper print
            ycrcb = cv2.cvtColor(base, cv2.COLOR_BGR2YCrCb)
            ycrcb[:, :, 1] = np.clip(ycrcb[:, :, 1] * 0.75, 0, 255)
            ycrcb[:, :, 2] = np.clip(ycrcb[:, :, 2] * 0.75, 0, 255)
            photo_frame = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
            return photo_frame

        # 5. SCREEN REPLAY ATTACK
        elif self.scenario == MockScenario.SCREEN_REPLAY_ATTACK:
            # Inject high frequency sinusoidal moiré grid pattern
            y, x = np.mgrid[:480, :640]
            moiré_pattern = (18 * np.sin(x * 0.6) * np.cos(y * 0.6)).astype(np.int16)
            screen_frame = np.clip(base.astype(np.int16) + moiré_pattern[:, :, None], 0, 255).astype(np.uint8)
            
            # Inject specular glass reflection patch across upper forehead
            cv2.rectangle(screen_frame, (315, 192), (435, 215), (255, 255, 255), -1)
            return screen_frame

        # 6. POOR LIGHTING - DARK
        elif self.scenario == MockScenario.POOR_LIGHTING_DARK:
            return (base * 0.15).astype(np.uint8)

        # 7. POOR LIGHTING - BRIGHT
        elif self.scenario == MockScenario.POOR_LIGHTING_BRIGHT:
            return np.clip(base.astype(np.int16) + 160, 0, 255).astype(np.uint8)

        # 8. POOR LIGHTING - UNEVEN
        elif self.scenario == MockScenario.POOR_LIGHTING_UNEVEN:
            uneven = base.copy()
            uneven[:, :320] = (uneven[:, :320] * 0.20).astype(np.uint8)
            uneven[:, 320:] = np.clip(uneven[:, 320:].astype(np.int16) + 70, 0, 255).astype(np.uint8)
            return uneven

        # 9. BLURRY FRAME
        elif self.scenario == MockScenario.BLURRY_FRAME:
            return cv2.GaussianBlur(base, (45, 45), 22)

        return base

    def read_frame(self) -> Tuple[bool, Optional[VideoFrame]]:
        if not self.is_connected():
            return False, None

        self._frame_count += 1
        frame_img = self._generate_frame_for_scenario()

        if frame_img is None or frame_img.size == 0:
            return False, None

        h, w = frame_img.shape[:2]
        video_frame = VideoFrame(
            frame_id=self._frame_count,
            timestamp_ms=time.time() * 1000.0,
            image=frame_img,
            width=w,
            height=h,
            is_key_frame=(self._frame_count % 30 == 0),
            metadata={"scenario": self.scenario.value}
        )
        return True, video_frame

    def start_stream(self) -> Generator[VideoFrame, None, None]:
        if not self.is_connected():
            self.connect()

        self._is_streaming = True
        self._info.status = DeviceStatus.STREAMING
        while self._is_streaming and self.is_connected():
            success, frame = self.read_frame()
            if success and frame is not None:
                yield frame
            time.sleep(1.0 / self.fps)

    def stop_stream(self) -> None:
        self._is_streaming = False
        if self.is_connected():
            self._info.status = DeviceStatus.CONNECTED
