"""
Structured Biometric Audit & Diagnostic Logger
Applies best-effort buffer and sensitive-key filtering:
- NEVER logs raw images, facial crops, or personal identifiable information (PII)
- Logs lifecycle security events with unique event IDs, ISO timestamps, and telemetry hashes
- Links event hashes; tamper detection requires a separately trusted checkpoint
"""

import json
import logging
import time
import uuid
import hashlib
import threading
from enum import Enum
from typing import Dict, Any, Optional


class AuditEventType(str, Enum):
    DEVICE_CONNECTED = "DEVICE_CONNECTED"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    CAPTURE_STARTED = "CAPTURE_STARTED"
    FACE_DETECTED = "FACE_DETECTED"
    QUALITY_CHECK = "QUALITY_CHECK"
    QUALITY_FAILED = "QUALITY_FAILED"
    PASSIVE_EVALUATED = "PASSIVE_EVALUATED"
    PASSIVE_PASSED = "PASSIVE_PASSED"
    ACTIVE_CHALLENGE_STARTED = "ACTIVE_CHALLENGE_STARTED"
    ACTIVE_CHALLENGE_PASSED = "ACTIVE_CHALLENGE_PASSED"
    ACTIVE_CHALLENGE_FAILED = "ACTIVE_CHALLENGE_FAILED"
    PAD_ATTACK_DETECTED = "PAD_ATTACK_DETECTED"
    CAPTURE_SUCCESS = "CAPTURE_SUCCESS"
    CAPTURE_REJECTED = "CAPTURE_REJECTED"


class BiometricAuditLogger:
    _instance: Optional['BiometricAuditLogger'] = None

    def __init__(self, log_to_console: bool = True, log_file: Optional[str] = None):
        self._lock = threading.Lock()
        self._last_hash = "0" * 64
        self.log_to_console = log_to_console
        self.log_file = log_file
        self._logger = logging.getLogger("MOSIP_BiometricAudit")
        self._logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if not self._logger.handlers:
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] [AUDIT] %(message)s')
            if log_to_console:
                ch = logging.StreamHandler()
                ch.setFormatter(formatter)
                self._logger.addHandler(ch)
            if log_file:
                fh = logging.FileHandler(log_file, encoding='utf-8')
                fh.setFormatter(formatter)
                self._logger.addHandler(fh)

    @classmethod
    def get_logger(cls) -> 'BiometricAuditLogger':
        if cls._instance is None:
            cls._instance = BiometricAuditLogger()
        return cls._instance

    def log_event(self,
                  event_type: AuditEventType,
                  session_id: Optional[str] = None,
                  workflow: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Emits a structured audit entry.
        Guarantees: Details dictionary must NEVER contain raw numpy arrays or image buffers.
        """
        def sanitize(value, depth=0):
            if depth > 8 or hasattr(value, "shape") or isinstance(value, (bytes, bytearray, memoryview)):
                return None
            if isinstance(value, dict):
                blocked = ("image", "frame", "pixel", "landmark", "resident", "name", "token", "secret", "password", "data")
                return {str(k): sanitize(v, depth + 1) for k, v in value.items()
                        if not any(word in str(k).lower() for word in blocked)}
            if isinstance(value, (list, tuple)):
                return [sanitize(v, depth + 1) for v in value[:100]]
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            return None
        clean_details = sanitize(details or {})

        entry = {
            "eventId": str(uuid.uuid4()),
            "timestamp": time.time(),
            "isoTimestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "eventType": event_type.value,
            "sessionId": session_id or "ANONYMOUS_SESSION",
            "workflow": workflow or "UNSPECIFIED",
            "details": clean_details
        }

        # Format as compact single-line JSON for machine parsing / SIEM ingestion
        with self._lock:
            entry["previousHash"] = self._last_hash
            digest = hashlib.sha256(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            entry["entryHash"] = digest
            self._last_hash = digest
            self._logger.info(json.dumps(entry))
        return entry
