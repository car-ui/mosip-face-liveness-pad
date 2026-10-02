"""
Modern Enterprise Desktop Registration Client UI (MOSIP Aligned)
Features a sleek glassmorphic biometric kiosk interface:
- Anti-aliased Apple FaceID / KYC style facial guide oval with optical alignment brackets
- Peripheral cinematic vignette focusing user attention
- Floating translucent glass status cards with dynamic feedback pills
- Directional indicator badges (arrows, icons) for active challenges
- Rounded capsule progress bars with animated tracking
- Clean enterprise status telemetry (ISO 19794-5 / ISO 30107)
"""

import sys
import time
import cv2
import numpy as np
from typing import Optional, Tuple

from ..devices.base import FaceCaptureDevice
from ..devices.webcam_device import WebcamCaptureDevice
from ..devices.mock_l0_device import MockL0Device
from ..core.pipeline import LivenessPipeline, PipelineState, PipelineStepResult
from ..core.config import WorkflowType, LivenessConfig


class DesktopRegistrationClient:
    def __init__(self, use_mock_device: bool = False):
        self.config = LivenessConfig()
        self.workflow = WorkflowType.RESIDENT_REGISTRATION
        self.pipeline = LivenessPipeline(self.config, self.workflow)
        
        self.use_mock_device = use_mock_device
        self.device: FaceCaptureDevice = MockL0Device() if use_mock_device else WebcamCaptureDevice(0)
        self.window_name = "MOSIP Registration Client - Face Liveness & PAD (Decode 04)"
        self.is_running = False

    def toggle_device(self):
        """Switches dynamically between Physical Webcam and Mock L0 Simulator."""
        self.device.disconnect()
        self.use_mock_device = not self.use_mock_device
        if self.use_mock_device:
            self.device = MockL0Device()
        else:
            self.device = WebcamCaptureDevice(0)
        
        if not self.device.connect():
            self.use_mock_device = True
            self.device = MockL0Device()
            self.device.connect()
        self.pipeline.reset()

    def set_workflow(self, wf: WorkflowType):
        self.workflow = wf
        self.pipeline.set_workflow(wf)

    def _draw_rounded_rect(self, img: np.ndarray, pt1: Tuple[int, int], pt2: Tuple[int, int],
                           color: Tuple[int, int, int], radius: int = 12, alpha: float = 1.0,
                           border_color: Optional[Tuple[int, int, int]] = None):
        """Draws an anti-aliased rounded rectangle with optional alpha transparency and border."""
        x1, y1 = pt1
        x2, y2 = pt2
        
        if alpha < 1.0:
            overlay = img.copy()
        else:
            overlay = img

        cv2.rectangle(overlay, (x1 + radius, y1), (x2 - radius, y2), color, -1)
        cv2.rectangle(overlay, (x1, y1 + radius), (x2, y2 - radius), color, -1)
        cv2.circle(overlay, (x1 + radius, y1 + radius), radius, color, -1, cv2.LINE_AA)
        cv2.circle(overlay, (x2 - radius, y1 + radius), radius, color, -1, cv2.LINE_AA)
        cv2.circle(overlay, (x1 + radius, y2 - radius), radius, color, -1, cv2.LINE_AA)
        cv2.circle(overlay, (x2 - radius, y2 - radius), radius, color, -1, cv2.LINE_AA)

        if border_color:
            cv2.line(overlay, (x1 + radius, y1), (x2 - radius, y1), border_color, 1, cv2.LINE_AA)
            cv2.line(overlay, (x1 + radius, y2), (x2 - radius, y2), border_color, 1, cv2.LINE_AA)
            cv2.line(overlay, (x1, y1 + radius), (x1, y2 - radius), border_color, 1, cv2.LINE_AA)
            cv2.line(overlay, (x2, y1 + radius), (x2, y2 - radius), border_color, 1, cv2.LINE_AA)
            cv2.ellipse(overlay, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, border_color, 1, cv2.LINE_AA)
            cv2.ellipse(overlay, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, border_color, 1, cv2.LINE_AA)
            cv2.ellipse(overlay, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, border_color, 1, cv2.LINE_AA)
            cv2.ellipse(overlay, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, border_color, 1, cv2.LINE_AA)

        if alpha < 1.0:
            cv2.addWeighted(overlay, alpha, img, 1.0 - alpha, 0, img)

    def _draw_badge(self, img: np.ndarray, text: str, pos: Tuple[int, int],
                    bg_color: Tuple[int, int, int], text_color: Tuple[int, int, int] = (255, 255, 255),
                    font_scale: float = 0.45, padding: int = 6):
        """Draws a pill-shaped status badge."""
        (w, h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, font_scale, 1)
        x, y = pos
        x2 = x + w + padding * 3
        y2 = y + h + padding * 2
        radius = (y2 - y) // 2
        self._draw_rounded_rect(img, (x, y), (x2, y2), bg_color, radius=radius, alpha=0.90, border_color=(80, 90, 110))
        cv2.putText(img, text, (x + padding * 2, y + h + padding - 1),
                    cv2.FONT_HERSHEY_DUPLEX, font_scale, text_color, 1, cv2.LINE_AA)
        return x2

    def _draw_cinematic_scanner(self, canvas: np.ndarray, center_x: int, center_y: int,
                                axis_x: int, axis_y: int, theme_accent: Tuple[int, int, int],
                                state: PipelineState) -> None:
        """Renders a cinematic laser scanning line sweeping top-to-bottom with a trailing holographic light curtain."""
        # Only sweep during face detection, passive evaluation, or active challenge
        if state not in (PipelineState.DETECTING_FACE, PipelineState.EVALUATING_PASSIVE, PipelineState.ACTIVE_CHALLENGE):
            return

        # Continuous smooth sweep from top to bottom (cycle duration ~1.6s)
        period = 1.6
        phase = (time.time() % period) / period  # 0.0 to 1.0
        
        # Current Y coordinate of the scan beam
        scan_y = int((center_y - axis_y + 14) + phase * (2 * axis_y - 28))
        dy = abs(scan_y - center_y)
        if dy >= axis_y:
            return

        # Width of the ellipse at scan_y
        dx = int(axis_x * np.sqrt(max(0.0, 1.0 - (dy / float(axis_y)) ** 2)))
        x1 = center_x - dx
        x2 = center_x + dx
        if x2 <= x1 + 10:
            return

        # 1. Trailing Holographic Light Curtain (semi-transparent gradient trailing upward)
        trail_height = 36
        roi_y1 = max(0, scan_y - trail_height)
        roi_y2 = min(canvas.shape[0], scan_y + 4)
        roi_x1 = max(0, center_x - axis_x - 10)
        roi_x2 = min(canvas.shape[1], center_x + axis_x + 10)

        if roi_y2 > roi_y1 and roi_x2 > roi_x1:
            roi = canvas[roi_y1:roi_y2, roi_x1:roi_x2].copy()
            for i in range(1, trail_height):
                trail_y = scan_y - i
                if trail_y < roi_y1:
                    break
                trail_dy = abs(trail_y - center_y)
                if trail_dy < axis_y:
                    t_dx = int(axis_x * np.sqrt(max(0.0, 1.0 - (trail_dy / float(axis_y)) ** 2)))
                    tx1 = max(0, center_x - t_dx - roi_x1)
                    tx2 = min(roi_x2 - roi_x1, center_x + t_dx - roi_x1)
                    local_y = trail_y - roi_y1
                    if tx2 > tx1 and 0 <= local_y < (roi_y2 - roi_y1):
                        decay = (1.0 - (i / float(trail_height))) ** 1.6
                        glow_color = tuple(int(c * decay * 0.85) for c in theme_accent)
                        cv2.line(roi, (tx1, local_y), (tx2, local_y), glow_color, 1)

            cv2.addWeighted(roi, 0.70, canvas[roi_y1:roi_y2, roi_x1:roi_x2], 0.30, 0, canvas[roi_y1:roi_y2, roi_x1:roi_x2])

        # 2. Glowing Outer Laser Beam
        cv2.line(canvas, (x1, scan_y), (x2, scan_y), theme_accent, 4, cv2.LINE_AA)

        # 3. High-Intensity White Core Beam
        bright_core = (
            min(255, theme_accent[0] + 120),
            min(255, theme_accent[1] + 120),
            min(255, theme_accent[2] + 120)
        )
        cv2.line(canvas, (x1, scan_y), (x2, scan_y), bright_core, 1, cv2.LINE_AA)

        # 4. Perimeter Laser Contact Nodes
        cv2.circle(canvas, (x1, scan_y), 4, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(canvas, (x1, scan_y), 7, theme_accent, 1, cv2.LINE_AA)
        cv2.circle(canvas, (x2, scan_y), 4, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(canvas, (x2, scan_y), 7, theme_accent, 1, cv2.LINE_AA)

        # 5. High-Tech HUD Telemetry Tag
        hud_label = "PASSIVE BIOMETRIC SCAN" if state == PipelineState.EVALUATING_PASSIVE else "LIVENESS ACTIVE VERIFY"
        cv2.putText(canvas, hud_label, (center_x - 76, scan_y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, bright_core, 1, cv2.LINE_AA)

    def draw_ui_overlay(self, frame: np.ndarray, result: PipelineStepResult) -> np.ndarray:
        # Resize to spacious kiosk resolution
        target_w, target_h = 960, 720
        canvas = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
        
        # Mirror webcam frame so user sees natural selfie view
        if not self.use_mock_device:
            canvas = cv2.flip(canvas, 1)

        center_x, center_y = target_w // 2, int(target_h * 0.47)
        axis_x, axis_y = int(target_w * 0.20), int(target_h * 0.31)

        # 1. Subtle peripheral darkening vignette (focuses user onto center)
        vignette_mask = np.zeros((target_h, target_w), dtype=np.uint8)
        cv2.ellipse(vignette_mask, (center_x, center_y), (axis_x, axis_y), 0, 0, 360, 255, -1)
        outside_mask = cv2.bitwise_not(vignette_mask)
        darkened_bg = (canvas * 0.45).astype(np.uint8)
        canvas = np.where(outside_mask[:, :, None] == 255, darkened_bg, canvas)

        # 2. Modern Palette based on State
        # BGR Colors
        theme_accent = (255, 190, 0)      # Electric Cyan
        theme_bg = (24, 28, 38)           # Slate Glass
        status_dot_color = (255, 190, 0)

        if result.state == PipelineState.CAPTURE_SUCCESS:
            theme_accent = (70, 230, 70)   # Vivid Emerald
            status_dot_color = (70, 230, 70)
        elif result.state in (PipelineState.ATTACK_REJECTED, PipelineState.MAX_RETRIES_EXCEEDED):
            theme_accent = (60, 60, 240)   # Vivid Coral Red
            status_dot_color = (60, 60, 240)
        elif result.state == PipelineState.ACTIVE_CHALLENGE:
            theme_accent = (0, 215, 255)   # Amber Gold
            status_dot_color = (0, 215, 255)
        elif result.state == PipelineState.RETRY_PENDING:
            theme_accent = (30, 140, 255)  # Orange
            status_dot_color = (30, 140, 255)
        elif result.quality and not result.quality.is_acceptable:
            theme_accent = (0, 165, 255)   # Amber Warning
            status_dot_color = (0, 165, 255)

        # 3. Double-Ring Facial Guide Oval
        cv2.ellipse(canvas, (center_x, center_y), (axis_x + 6, axis_y + 6), 0, 0, 360, (50, 60, 80), 1, cv2.LINE_AA)
        cv2.ellipse(canvas, (center_x, center_y), (axis_x, axis_y), 0, 0, 360, theme_accent, 3, cv2.LINE_AA)

        # Corner Alignment Brackets around Oval
        bracket_len = 22
        b_x1 = center_x - axis_x - 14
        b_x2 = center_x + axis_x + 14
        b_y1 = center_y - axis_y - 14
        b_y2 = center_y + axis_y + 14

        # Top-Left Bracket
        cv2.line(canvas, (b_x1, b_y1), (b_x1 + bracket_len, b_y1), theme_accent, 2, cv2.LINE_AA)
        cv2.line(canvas, (b_x1, b_y1), (b_x1, b_y1 + bracket_len), theme_accent, 2, cv2.LINE_AA)
        # Top-Right Bracket
        cv2.line(canvas, (b_x2, b_y1), (b_x2 - bracket_len, b_y1), theme_accent, 2, cv2.LINE_AA)
        cv2.line(canvas, (b_x2, b_y1), (b_x2, b_y1 + bracket_len), theme_accent, 2, cv2.LINE_AA)
        # Bottom-Left Bracket
        cv2.line(canvas, (b_x1, b_y2), (b_x1 + bracket_len, b_y2), theme_accent, 2, cv2.LINE_AA)
        cv2.line(canvas, (b_x1, b_y2), (b_x1, b_y2 - bracket_len), theme_accent, 2, cv2.LINE_AA)
        # Bottom-Right Bracket
        cv2.line(canvas, (b_x2, b_y2), (b_x2 - bracket_len, b_y2), theme_accent, 2, cv2.LINE_AA)
        cv2.line(canvas, (b_x2, b_y2), (b_x2, b_y2 - bracket_len), theme_accent, 2, cv2.LINE_AA)

        # 3b. Cinematic Laser Scanner (Top-to-Bottom Biometric Verification Sweep)
        self._draw_cinematic_scanner(canvas, center_x, center_y, axis_x, axis_y, theme_accent, result.state)

        # 4. TOP GLASS CARD: MOSIP Header & Telemetry
        self._draw_rounded_rect(canvas, (24, 20), (target_w - 24, 82), (18, 22, 32),
                                radius=14, alpha=0.88, border_color=(45, 55, 75))
        
        # Logo / Branding
        cv2.putText(canvas, "MOSIP DEC{}DE", (44, 57),
                    cv2.FONT_HERSHEY_DUPLEX, 0.72, (255, 90, 30), 2, cv2.LINE_AA)
        cv2.putText(canvas, "FACE LIVENESS & PAD", (230, 56),
                    cv2.FONT_HERSHEY_DUPLEX, 0.48, (200, 210, 230), 1, cv2.LINE_AA)

        # Right Badges (Workflow, Device, Attempts)
        badge_x = target_w - 530
        badge_x = self._draw_badge(canvas, self.workflow.value.replace("_", " "), (badge_x, 34),
                                    (35, 45, 65), (230, 240, 255), 0.38) + 10
        
        dev_label = "MOCK SIMULATOR" if self.use_mock_device else "L0 WEBCAM"
        badge_x = self._draw_badge(canvas, dev_label, (badge_x, 34),
                                    (30, 50, 45), (70, 230, 140), 0.38) + 10

        retry_color = (60, 35, 40) if result.current_retry > 1 else (35, 45, 60)
        self._draw_badge(canvas, f"ATTEMPT {result.current_retry + 1}/{result.max_retries}", (badge_x, 34),
                         retry_color, (230, 220, 230), 0.38)

        # 5. FLOATING ACTION CARD (Prominently Above / Below Center)
        card_w = 680
        card_h = 76
        c_x1 = (target_w - card_w) // 2
        c_y1 = int(target_h * 0.76)
        c_x2 = c_x1 + card_w
        c_y2 = c_y1 + card_h

        self._draw_rounded_rect(canvas, (c_x1, c_y1), (c_x2, c_y2), (18, 22, 32),
                                radius=16, alpha=0.92, border_color=(55, 65, 85))

        # Status Glowing Dot
        cv2.circle(canvas, (c_x1 + 32, c_y1 + 38), 9, status_dot_color, -1, cv2.LINE_AA)
        cv2.circle(canvas, (c_x1 + 32, c_y1 + 38), 14, status_dot_color, 1, cv2.LINE_AA)

        # Primary Status Prompt
        cv2.putText(canvas, result.status_text, (c_x1 + 56, c_y1 + 35),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)

        # Secondary Detailed Guidance
        cv2.putText(canvas, result.detailed_guidance, (c_x1 + 56, c_y1 + 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (165, 175, 195), 1, cv2.LINE_AA)

        # Capsule Progress Bar inside Action Card
        bar_x = c_x2 - 140
        bar_y = c_y1 + 26
        bar_w = 110
        bar_h = 10
        # Track
        self._draw_rounded_rect(canvas, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                                (35, 42, 55), radius=5, alpha=1.0)
        # Fill
        fill_w = int(bar_w * max(0.04, min(1.0, result.progress)))
        self._draw_rounded_rect(canvas, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h),
                                theme_accent, radius=5, alpha=1.0)
        # Percentage label
        pct_text = f"{int(result.progress * 100)}%"
        cv2.putText(canvas, pct_text, (bar_x + 35, bar_y + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 190, 210), 1, cv2.LINE_AA)

        # 6. FLOATING BOTTOM FOOTER: Hotkey Legend & Standards
        self._draw_rounded_rect(canvas, (24, target_h - 52), (target_w - 24, target_h - 16),
                                (16, 20, 28), radius=10, alpha=0.88, border_color=(40, 50, 68))
        
        controls = "[R] Reset Session   |   [1] Resident   [2] Operator   [3] Supervisor   |   [Q] Exit"
        cv2.putText(canvas, controls, (42, target_h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 160, 180), 1, cv2.LINE_AA)
        
        iso_tag = "ISO/IEC 30107-3 | ISO/IEC 19794-5"
        cv2.putText(canvas, iso_tag, (target_w - 275, target_h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (110, 120, 140), 1, cv2.LINE_AA)

        # 7. SUCCESS CELEBRATION MODAL
        if result.state == PipelineState.CAPTURE_SUCCESS:
            modal_w = 460
            modal_h = 130
            m_x1 = (target_w - modal_w) // 2
            m_y1 = center_y - (modal_h // 2)
            m_x2 = m_x1 + modal_w
            m_y2 = m_y1 + modal_h

            self._draw_rounded_rect(canvas, (m_x1, m_y1), (m_x2, m_y2), (15, 28, 20),
                                    radius=18, alpha=0.96, border_color=(70, 230, 110))
            
            # Checkmark circle icon
            cv2.circle(canvas, (m_x1 + 45, m_y1 + modal_h // 2), 22, (50, 200, 90), -1, cv2.LINE_AA)
            cv2.putText(canvas, "OK", (m_x1 + 32, m_y1 + modal_h // 2 + 7),
                        cv2.FONT_HERSHEY_DUPLEX, 0.60, (10, 30, 15), 2, cv2.LINE_AA)

            cv2.putText(canvas, "BIOMETRIC VERIFIED", (m_x1 + 85, m_y1 + 46),
                        cv2.FONT_HERSHEY_DUPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(canvas, "Liveness Confirmed • Token Encrypted", (m_x1 + 86, m_y1 + 72),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (120, 220, 150), 1, cv2.LINE_AA)
            cv2.putText(canvas, "Press [R] to start a new session", (m_x1 + 86, m_y1 + 96),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 175, 190), 1, cv2.LINE_AA)

        return canvas

    def start(self):
        print(f"Connecting to capture device: {self.device.get_device_info().device_name}...")
        if not self.device.connect():
            print("Primary device failed to open, switching to Mock L0 simulator...")
            self.device = MockL0Device()
            self.device.connect()
            self.use_mock_device = True

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 960, 720)
        self.is_running = True
        self.pipeline.reset()

        print("\n=== MOSIP Face Liveness Client Started ===")
        print("Hotkeys:")
        print("  'r' - Reset verification session")
        print("  '1' - Resident Registration Workflow")
        print("  '2' - Operator Authentication Workflow")
        print("  '3' - Supervisor Authentication Workflow")
        print("  'q' - Quit\n")

        try:
            while self.is_running:
                success, frame = self.device.read_frame()
                if not success or frame is None:
                    time.sleep(0.01)
                    continue

                # Run Liveness & PAD pipeline
                result = self.pipeline.process_frame(frame)
                
                # Render Clean Modern UI
                display = self.draw_ui_overlay(frame.image, result)
                cv2.imshow(self.window_name, display)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # Esc or Q
                    break
                # Detect if user clicked the 'X' button on the OpenCV window
                if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
                elif key == ord('r'):
                    self.pipeline.reset()
                elif key == ord('1'):
                    self.set_workflow(WorkflowType.RESIDENT_REGISTRATION)
                elif key == ord('2'):
                    self.set_workflow(WorkflowType.OPERATOR_AUTHENTICATION)
                elif key == ord('3'):
                    self.set_workflow(WorkflowType.SUPERVISOR_AUTHENTICATION)

        finally:
            self.device.disconnect()
            cv2.destroyAllWindows()
            print("MOSIP Face Liveness Client exited safely.")


if __name__ == "__main__":
    client = DesktopRegistrationClient(use_mock_device=False)
    client.start()
