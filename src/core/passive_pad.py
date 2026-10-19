"""
Modular Passive Liveness & Presentation Attack Detection (PAD) Engine
Designed to align with ISO/IEC 30107 principles (Level 1 / Level 2 attack vectors):
- Printed photograph attacks (paper texture, color gamut clipping, lack of micro-variation)
- Digital screen replay attacks (moiré patterns, refresh artifacts, specular glass reflections)
- 2D planar attacks vs natural anatomical facial reflectance and depth variation

Supports:
1. Pluggable ONNX Deep Learning model inference (e.g., MiniFASNet / Silent-Face-Anti-Spoofing)
2. Hardware acceleration discovery (DirectML, CUDA, OpenVINO, CPU)
3. Model versioning and cryptographic SHA-256 hash tracking
4. Multi-cue deterministic physical heuristic engine fallback
5. Explicit execution mode reporting ('MODEL' or 'HEURISTIC')
6. Heuristic confidence scores and explicit 4-way classification:
   - BONA_FIDE_LIVE
   - UNCERTAIN
   - PRESENTATION_ATTACK
   - PROCESSING_ERROR
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, List
import os
import cv2
import numpy as np
import hashlib
import json
import time

from .config import PADMode, PADVerdict


@dataclass
class ModelMetadata:
    """Model and backend provenance tracking for biometric audit compliance."""
    backend_name: str           # "onnx_deep_learning" or "heuristic_multi_cue"
    version: str                # e.g. "v1.0.0-onnx" or "v1.2.0-heuristic"
    model_hash: str             # Cryptographic SHA-256 hex digest or descriptive identifier
    input_size: Tuple[int, int] # (width, height)
    inference_provider: str     # Hardware acceleration provider used (e.g. CPUExecutionProvider)
    threshold: float            # Decision boundary threshold
    timestamp: float = field(default_factory=time.time)


@dataclass
class PADResult:
    verdict: PADVerdict
    is_live: bool
    liveness_score: float      # 0.0 (definite attack) to 1.0 (definite bona fide live)
    confidence: float          # Score-derived confidence, not calibrated population probability
    attack_detected: bool
    attack_type: Optional[str] # "PRINT_PHOTO", "SCREEN_REPLAY", "NONE"
    mode_used: str             # "MODEL" or "HEURISTIC"
    details: Dict[str, Any] = field(default_factory=dict)
    model_metadata: Optional[ModelMetadata] = None
    processing_time_ms: float = 0.0


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

    @abstractmethod
    def get_metadata(self) -> ModelMetadata:
        """Returns model version and backend metadata."""
        pass


class ONNXModelPADBackend(BasePADBackend):
    """
    Research ONNX Runtime inference backend for Deep Learning PAD models.
    Supports hardware-accelerated providers (CUDA, DirectML, OpenVINO, CPU) and SHA-256 checksums.
    """

    def __init__(self, model_path: Optional[str] = None, input_size: Tuple[int, int] = (224, 224)):
        self.model_path = model_path
        self.input_size = input_size
        self._session = None
        self._input_name = None
        self._output_name = None
        self._active_provider = "N/A"
        self._model_hash = "N/A"
        self._model_version = "v1.0.0-onnx"
        self.profile = "binary_imagenet"
        self.live_index = 0
        self.class_count = 2
        self.crop_scale = 1.0
        self.output_kind = "logits"
        self._init_session()

    def _init_session(self) -> None:
        if not self.model_path or not os.path.exists(self.model_path):
            return

        try:
            import onnxruntime as ort
            # Discover and prioritize hardware acceleration providers
            available = ort.get_available_providers()
            desired_providers = [
                'CUDAExecutionProvider',
                'DirectMLExecutionProvider',
                'OpenVINOExecutionProvider',
                'CPUExecutionProvider'
            ]
            selected_providers = [p for p in desired_providers if p in available]
            if not selected_providers:
                selected_providers = ['CPUExecutionProvider']

            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
            self._session = ort.InferenceSession(self.model_path, opts, providers=selected_providers)
            self._active_provider = self._session.get_providers()[0] if self._session.get_providers() else "CPUExecutionProvider"
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name

            # Calculate SHA-256 hash of model file for audit provenance
            hasher = hashlib.sha256()
            with open(self.model_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            self._model_hash = hasher.hexdigest()
            manifest_path = self.model_path + ".json"
            if os.path.exists(manifest_path):
                with open(manifest_path, encoding="utf-8") as stream:
                    manifest = json.load(stream)
                if manifest["sha256"] != self._model_hash:
                    raise ValueError("Model manifest checksum mismatch")
                if manifest["profile"] not in ("minifasnet_v2_2.7", "minifasnet_v1se_4.0", "anti_spoof_mn3"):
                    raise ValueError("Unsupported model profile")
                self.profile = manifest["profile"]
                if self.profile == "anti_spoof_mn3":
                    self.input_size = (128, 128)
                    self.live_index, self.class_count = 0, 2
                    self.crop_scale = 1.0
                    self.output_kind = "probabilities"
                else:
                    self.input_size = (80, 80)
                    self.live_index, self.class_count = 1, 3
                    self.crop_scale = 4.0 if self.profile == "minifasnet_v1se_4.0" else 2.7
                self._model_version = manifest["version"]
            expected = [1, 3, self.input_size[1], self.input_size[0]]
            if self._session.get_inputs()[0].shape != expected:
                raise ValueError("Model input dimensions do not match preprocessing")
        except Exception:
            self._session = None
            self._active_provider = "N/A"
            self._model_hash = "N/A"

    def is_available(self) -> bool:
        return self._session is not None

    def get_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            backend_name="onnx_deep_learning",
            version=self._model_version,
            model_hash=self._model_hash,
            input_size=self.input_size,
            inference_provider=self._active_provider,
            threshold=0.50
        )

    def evaluate(self, bgr_face: np.ndarray) -> Tuple[float, float, bool, Optional[str], Dict[str, Any]]:
        if not self.is_available():
            raise RuntimeError("ONNX PAD Backend is not available.")

        # Standard preprocessing: BGR -> RGB -> Resize -> Normalize to [0, 1]
        rgb = (bgr_face if self.profile in ("minifasnet_v2_2.7", "minifasnet_v1se_4.0")
               else cv2.cvtColor(bgr_face, cv2.COLOR_BGR2RGB))
        resized = cv2.resize(rgb, self.input_size, interpolation=cv2.INTER_LINEAR)
        
        # Standard mean/std normalization
        normalized = resized.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (normalized - mean) / std
        if self.profile in ("minifasnet_v2_2.7", "minifasnet_v1se_4.0"):
            # Upstream functional.to_tensor explicitly returns BGR float [0,255].
            normalized = resized.astype(np.float32)
        elif self.profile == "anti_spoof_mn3":
            normalized = (resized.astype(np.float32) - np.array(
                [151.2405, 119.595, 107.8395], dtype=np.float32)) / np.array(
                [63.0105, 56.457, 55.0035], dtype=np.float32)

        # Transpose to NCHW format
        blob = np.transpose(normalized, (2, 0, 1))
        blob = np.expand_dims(blob, axis=0).astype(np.float32)

        # Execute ONNX forward pass
        raw_outputs = self._session.run([self._output_name], {self._input_name: blob})[0]
        logits = raw_outputs.flatten()
        if len(logits) != self.class_count or not np.isfinite(logits).all():
            raise ValueError("Model output does not match its declared class contract")

        # Compute Softmax
        if self.output_kind == "probabilities":
            if (np.any(logits < 0) or np.any(logits > 1)
                    or not np.isclose(np.sum(logits), 1.0, atol=1e-4)):
                raise ValueError("Invalid output probabilities")
            probs = logits
        else:
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / np.sum(exp_logits)

        # Binary output assumption: [prob_live, prob_spoof]
        if len(probs) >= 2:
            live_score = float(probs[self.live_index])
            spoof_score = 1.0 - live_score
        else:
            live_score = float(probs[0])
            spoof_score = 1.0 - live_score

        attack_detected = live_score < 0.40
        attack_type = "PRESENTATION_ATTACK" if attack_detected else None
        confidence = float(abs(live_score - 0.5) * 2.0)

        details = {
            "model_type": "ONNX_DEEP_LEARNING",
            "profile": self.profile,
            "output_kind": self.output_kind,
            "model_path": os.path.basename(self.model_path or ""),
            "model_hash": self._model_hash[:16] + "..." if self._model_hash != "N/A" else "N/A",
            "inference_provider": self._active_provider,
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

    def get_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            backend_name="heuristic_multi_cue",
            version="v1.2.0-heuristic",
            model_hash="N/A - Deterministic Algorithmic Cues",
            input_size=(128, 128),
            inference_provider="NumPy/OpenCV-CPU",
            threshold=0.50
        )

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
    Manages operational backends, calibrated confidence, model version metadata,
    and 4-way decision classifications.
    """

    def __init__(self,
                 onnx_model_path: Optional[str] = None,
                 mode: PADMode = PADMode.AUTO,
                 high_confidence_threshold: float = 0.85,
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
        Returns complete, structured PADResult with 4-way verdict and model provenance metadata.
        """
        t_start = time.time()
        x, y, w, h = face_box
        img_h, img_w = bgr_frame.shape[:2]

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + w)
        y2 = min(img_h, y + h)

        face_crop = bgr_frame[y1:y2, x1:x2]
        active_backend = self._heuristic_backend
        active_mode = self.operational_mode
        if active_mode == "MODEL" and self._onnx_backend.crop_scale > 1:
            # Preserve the surrounding presentation medium, as required by this model.
            scale = min((img_h - 1) / h, (img_w - 1) / w, self._onnx_backend.crop_scale)
            crop_w, crop_h = w * scale, h * scale
            left, top = x + w / 2 - crop_w / 2, y + h / 2 - crop_h / 2
            right, bottom = left + crop_w, top + crop_h
            if left < 0:
                right -= left
                left = 0
            if top < 0:
                bottom -= top
                top = 0
            if right > img_w - 1:
                left -= right - img_w + 1
                right = img_w - 1
            if bottom > img_h - 1:
                top -= bottom - img_h + 1
                bottom = img_h - 1
            face_crop = bgr_frame[int(top):int(bottom) + 1, int(left):int(right) + 1]

        # Enforce safe failure if ONNX_ONLY is requested but no model is loaded
        if self.mode == PADMode.ONNX_ONLY and not self._onnx_backend.is_available():
            proc_ms = round((time.time() - t_start) * 1000.0, 2)
            return PADResult(
                verdict=PADVerdict.PROCESSING_ERROR,
                is_live=False,
                liveness_score=0.0,
                confidence=0.0,
                attack_detected=False,
                attack_type=None,
                mode_used="MODEL_UNAVAILABLE",
                details={"error": "ONNX_ONLY mode configured but no valid ONNX model file exists"},
                model_metadata=self._onnx_backend.get_metadata(),
                processing_time_ms=proc_ms
            )

        if face_crop.size == 0 or face_crop.shape[0] < 35 or face_crop.shape[1] < 35:
            proc_ms = round((time.time() - t_start) * 1000.0, 2)
            return PADResult(
                verdict=PADVerdict.PROCESSING_ERROR,
                is_live=False,
                liveness_score=0.0,
                confidence=0.0,
                attack_detected=False,
                attack_type=None,
                mode_used=active_mode,
                details={"error": "Face region invalid or too small"},
                model_metadata=active_backend.get_metadata(),
                processing_time_ms=proc_ms
            )

        if active_mode == "MODEL" and self._onnx_backend.is_available():
            try:
                score, conf, attack_detected, attack_type, details = self._onnx_backend.evaluate(face_crop)
                active_backend = self._onnx_backend
            except Exception as e:
                if self.mode == PADMode.ONNX_ONLY:
                    return PADResult(
                        verdict=PADVerdict.PROCESSING_ERROR, is_live=False,
                        liveness_score=0.0, confidence=0.0, attack_detected=False,
                        attack_type=None, mode_used="MODEL_ERROR",
                        details={"error": "ONNX inference failed"},
                        model_metadata=self._onnx_backend.get_metadata(),
                        processing_time_ms=(time.time() - t_start) * 1000.0,
                    )
                # Fallback to heuristic on model exception
                score, conf, attack_detected, attack_type, details = self._heuristic_backend.evaluate(face_crop)
                active_mode = "HEURISTIC"
                active_backend = self._heuristic_backend
                details["fallback_reason"] = str(e)
        else:
            score, conf, attack_detected, attack_type, details = self._heuristic_backend.evaluate(face_crop)
            active_mode = "HEURISTIC"
            active_backend = self._heuristic_backend

        if not np.isfinite([score, conf]).all() or not 0 <= score <= 1 or not 0 <= conf <= 1:
            return PADResult(
                verdict=PADVerdict.PROCESSING_ERROR, is_live=False,
                liveness_score=0.0, confidence=0.0, attack_detected=False,
                attack_type=None, mode_used=active_mode,
                details={"error": "Invalid PAD scores"},
                model_metadata=active_backend.get_metadata(),
            )
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

        proc_ms = round((time.time() - t_start) * 1000.0, 2)
        return PADResult(
            verdict=verdict,
            is_live=is_live,
            liveness_score=round(score, 3),
            confidence=round(conf, 3),
            attack_detected=(verdict == PADVerdict.PRESENTATION_ATTACK),
            attack_type=attack_type,
            mode_used=active_mode,
            details=details,
            model_metadata=active_backend.get_metadata(),
            processing_time_ms=proc_ms
        )
