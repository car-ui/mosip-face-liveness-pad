"""
Modular Passive Liveness & Presentation Attack Detection (PAD) Engine
Designed to align with ISO/IEC 30107 principles (Level 1 / Level 2 attack vectors):
- Printed photograph attacks (paper texture, color gamut clipping, lack of micro-variation)
- Digital screen replay attacks (moiré patterns, refresh artifacts, specular glass reflections)
- 2D planar attacks vs natural 3D anatomical reflectance

Supports:
1. Pluggable ONNX Deep Learning model inference (e.g., MiniFASNet / Silent-Face-Anti-Spoofing)
2. Multi-cue deterministic physical heuristic engine fallback
3. Explicit execution mode reporting ('MODEL' or 'HEURISTIC')
4. Calibrated confidence scoring and clear 4-way classification:
   - BONA_FIDE_LIVE
   - UNCERTAIN
   - PRESENTATION_ATTACK
   - PROCESSING_ERROR
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any
import os
import cv2
import numpy as np

from .config import PADMode, PADVerdict


@dataclass
class PADResult:
    verdict: PADVerdict
    is_live: bool
    liveness_score: float      # 0.0 (definite attack) to 1.0 (definite bona fide live)
    confidence: float          # Calibrated confidence 0.0 to 1.0
    attack_detected: bool
    attack_type: Optional[str] # "PRINT_PHOTO", "SCREEN_REPLAY", "NONE"
    mode_used: str             # "MODEL" or "HEURISTIC"
    details: Dict[str, Any] = field(default_factory=dict)


class BasePADBackend(ABC):
    """Abstract interface for Passive PAD backends."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the backend is initialized and ready to run."""
        pass

    @abstractmethod
    def evaluate(self, bgr_face: np.ndarray) -> Tuple[float, float, bool, Optional[str], Dict[str, Any]]:
        """
        Evaluates a cropped face region.
        Returns: (liveness_score, confidence, attack_detected, attack_type, details_dict)
        """
        pass


class ONNXModelPADBackend(BasePADBackend):
    """
    Production-grade ONNX Runtime inference backend for Deep Learning PAD models.
    Supports standard deep anti-spoofing architectures (e.g. 224x224 or 128x128 input).
    """

    def __init__(self, model_path: Optional[str] = None, input_size: Tuple[int, int] = (224, 224)):
        self.model_path = model_path
        self.input_size = input_size
        self._session = None
        self._input_name = None
        self._output_name = None
        self._init_session()

    def _init_session(self) -> None:
        if not self.model_path or not os.path.exists(self.model_path):
            return

        try:
            import onnxruntime as ort
            # Use lightweight CPU provider for universal compatibility
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
            self._session = ort.InferenceSession(self.model_path, opts, providers=['CPUExecutionProvider'])
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
        except Exception:
            self._session = None

    def is_available(self) -> bool:
        return self._session is not None

    def evaluate(self, bgr_face: np.ndarray) -> Tuple[float, float, bool, Optional[str], Dict[str, Any]]:
        if not self.is_available():
            raise RuntimeError("ONNX PAD Backend is not available.")

        # Standard preprocessing: BGR -> RGB -> Resize -> Normalize to [0, 1]
        rgb = cv2.cvtColor(bgr_face, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, self.input_size, interpolation=cv2.INTER_LINEAR)
        
        # Standard mean/std normalization
        normalized = resized.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (normalized - mean) / std

        # Transpose to NCHW format
        blob = np.transpose(normalized, (2, 0, 1))
        blob = np.expand_dims(blob, axis=0).astype(np.float32)

        # Execute ONNX forward pass
        raw_outputs = self._session.run([self._output_name], {self._input_name: blob})[0]
        logits = raw_outputs.flatten()

        # Compute Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        
        # Assume standard 2-class classifier [spoof_prob, live_prob]
        if len(probs) >= 2:
            live_score = float(probs[1])
            spoof_score = float(probs[0])
        else:
            live_score = float(probs[0])
            spoof_score = 1.0 - live_score

        attack_detected = live_score < 0.40
        attack_type = "PRESENTATION_ATTACK" if attack_detected else None
        confidence = float(abs(live_score - 0.5) * 2.0)  # Distance from decision boundary

        details = {
            "model_type": "ONNX_DEEP_LEARNING",
            "model_path": os.path.basename(self.model_path or ""),
            "live_prob": round(live_score, 4),
            "spoof_prob": round(spoof_score, 4)
        }
        return live_score, confidence, attack_detected, attack_type, details


class HeuristicPADBackend(BasePADBackend):
    """
    Multi-cue physical texture and optical analysis engine.
    Used as a deterministic offline fallback or standalone evaluation mechanism.
    Analyzes:
    1. 2D Discrete Fourier Transform (DFT) for frequency moiré & halftone patterns
    2. YCrCb & HSV chrominance gamut distribution
    3. Specular screen reflection & glare
    4. Sobel micro-texture gradient distribution
    """

    def is_available(self) -> bool:
        return True

    def _analyze_frequency_moire(self, gray_face: np.ndarray) -> float:
        """2D DFT analysis for high-frequency screen grids or print halftone patterns."""
        resized = cv2.resize(gray_face, (128, 128))
        dft = cv2.dft(np.float32(resized), flags=cv2.DFT_COMPLEX_OUTPUT)
        dft_shift = np.fft.fftshift(dft)
        mag = 20 * np.log(cv2.magnitude(dft_shift[:, :, 0], dft_shift[:, :, 1]) + 1.0)

        center = 64
        mask_radius = 20
        y, x = np.ogrid[:128, :128]
        dist = np.sqrt((x - center)**2 + (y - center)**2)

        high_freq = dist > mask_radius
        high_energy = float(np.mean(mag[high_freq]))
        total_energy = float(np.mean(mag)) + 1e-6
        ratio = high_energy / total_energy

        # Moiré and digital displays create unnatural harmonic peaks
        score = np.clip(1.0 - (abs(ratio - 0.72) * 2.5), 0.1, 0.98)
        return float(score)

    def _analyze_chrominance(self, bgr_face: np.ndarray) -> float:
        """Analyzes subcutaneous hemoglobin reflectance vs flat dye/LED gamut."""
        ycrcb = cv2.cvtColor(bgr_face, cv2.COLOR_BGR2YCrCb)
        cr_std = float(np.std(ycrcb[:, :, 1]))
        cb_std = float(np.std(ycrcb[:, :, 2]))
        chroma_var = (cr_std + cb_std) / 2.0

        if chroma_var < 5.0:
            return 0.35  # Crushed/flat print
        elif chroma_var > 34.0:
            return 0.45  # Saturated digital display
        return 0.90      # Natural live skin variance

    def _analyze_specular_glare(self, bgr_face: np.ndarray) -> Tuple[float, bool]:
        """Detects planar glass or glossy print specular reflection highlights."""
        gray = cv2.cvtColor(bgr_face, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 252, 255, cv2.THRESH_BINARY)
        glare_ratio = float(np.sum(thresh > 0)) / float(gray.size)

        has_glare = glare_ratio > 0.075
        glare_score = 0.38 if has_glare else 0.95
        return float(glare_score), has_glare

    def _analyze_texture_gradients(self, gray_face: np.ndarray) -> float:
        """Analyzes micro-texture gradient magnitudes across facial epidermis."""
        sobel_x = cv2.Sobel(gray_face, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray_face, cv2.CV_64F, 0, 1, ksize=3)
        grad_mean = float(np.mean(np.sqrt(sobel_x**2 + sobel_y**2)))
        return float(np.clip(grad_mean / 42.0, 0.2, 0.95))

    def evaluate(self, bgr_face: np.ndarray) -> Tuple[float, float, bool, Optional[str], Dict[str, Any]]:
        gray_face = cv2.cvtColor(bgr_face, cv2.COLOR_BGR2GRAY)

        freq_score = self._analyze_frequency_moire(gray_face)
        color_score = self._analyze_chrominance(bgr_face)
        glare_score, has_glare = self._analyze_specular_glare(bgr_face)
        texture_score = self._analyze_texture_gradients(gray_face)

        # Weighted combination of independent cues
        composite = (
            0.35 * freq_score +
            0.25 * color_score +
            0.25 * glare_score +
            0.15 * texture_score
        )
        composite = float(np.clip(composite, 0.0, 1.0))

        # Multi-cue attack detection logic
        attack_detected = False
        attack_type = None

        if has_glare and freq_score < 0.45:
            attack_detected = True
            attack_type = "SCREEN_REPLAY"
            composite = min(composite, 0.38)
        elif color_score < 0.38 and texture_score < 0.25:
            attack_detected = True
            attack_type = "PRINT_PHOTO"
            composite = min(composite, 0.38)

        # Confidence calibration: variance among cues
        cues = [freq_score, color_score, glare_score, texture_score]
        cue_std = float(np.std(cues))
        # High confidence when all cues agree
        confidence = float(np.clip(1.0 - (cue_std * 1.5), 0.55, 0.98))

        details = {
            "frequency_score": round(freq_score, 3),
            "chroma_score": round(color_score, 3),
            "glare_score": round(glare_score, 3),
            "texture_score": round(texture_score, 3),
            "has_glare": has_glare
        }
        return composite, confidence, attack_detected, attack_type, details


class PassivePADDetector:
    """
    Master Presentation Attack Detection Orchestrator.
    Manages ONNX and Heuristic backends, provides clean 4-way verdict classification,
    and transparently reports active operational mode.
    """

    def __init__(self,
                 onnx_model_path: Optional[str] = None,
                 mode: PADMode = PADMode.AUTO,
                 high_confidence_threshold: float = 0.82,
                 attack_threshold: float = 0.45):
        self.mode = mode
        self.high_confidence_threshold = high_confidence_threshold
        self.attack_threshold = attack_threshold

        self._onnx_backend = ONNXModelPADBackend(onnx_model_path)
        self._heuristic_backend = HeuristicPADBackend()

    @property
    def operational_mode(self) -> str:
        """Reports whether the system is actively running via deep learning MODEL or HEURISTIC."""
        if self.mode == PADMode.ONNX_ONLY:
            return "MODEL"
        elif self.mode == PADMode.HEURISTIC_ONLY:
            return "HEURISTIC"
        elif self.mode == PADMode.AUTO and self._onnx_backend.is_available():
            return "MODEL"
        return "HEURISTIC"

    def evaluate_passive_liveness(self,
                                  bgr_frame: np.ndarray,
                                  face_box: Tuple[int, int, int, int]) -> PADResult:
        """
        Evaluates a detected face crop.
        Returns complete, structured PADResult with 4-way verdict.
        """
        x, y, w, h = face_box
        img_h, img_w = bgr_frame.shape[:2]

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + w)
        y2 = min(img_h, y + h)

        face_crop = bgr_frame[y1:y2, x1:x2]
        if face_crop.size == 0 or face_crop.shape[0] < 35 or face_crop.shape[1] < 35:
            return PADResult(
                verdict=PADVerdict.PROCESSING_ERROR,
                is_live=False,
                liveness_score=0.0,
                confidence=0.0,
                attack_detected=False,
                attack_type=None,
                mode_used=self.operational_mode,
                details={"error": "Face region invalid or too small"}
            )

        active_mode = self.operational_mode
        if active_mode == "MODEL" and self._onnx_backend.is_available():
            try:
                score, conf, attack_detected, attack_type, details = self._onnx_backend.evaluate(face_crop)
            except Exception as e:
                # Fallback to heuristic on model exception
                score, conf, attack_detected, attack_type, details = self._heuristic_backend.evaluate(face_crop)
                active_mode = "HEURISTIC"
                details["fallback_reason"] = str(e)
        else:
            score, conf, attack_detected, attack_type, details = self._heuristic_backend.evaluate(face_crop)
            active_mode = "HEURISTIC"

        # 4-Way Verdict Classification
        if attack_detected or score <= self.attack_threshold:
            verdict = PADVerdict.PRESENTATION_ATTACK
            is_live = False
        elif score >= self.high_confidence_threshold:
            verdict = PADVerdict.BONA_FIDE_LIVE
            is_live = True
        else:
            verdict = PADVerdict.UNCERTAIN
            is_live = False

        return PADResult(
            verdict=verdict,
            is_live=is_live,
            liveness_score=round(score, 3),
            confidence=round(conf, 3),
            attack_detected=(verdict == PADVerdict.PRESENTATION_ATTACK),
            attack_type=attack_type,
            mode_used=active_mode,
            details=details
        )
