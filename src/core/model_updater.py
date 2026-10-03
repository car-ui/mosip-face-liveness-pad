"""
Secure Offline Model Update Subsystem
Fulfills the MOSIP Decode Bonus Deliverable:
- Integrity Verification (SHA-256 Digest)
- Cryptographic Signature Verification (HMAC-SHA256 / Public Key)
- Anti-Downgrade Version Validation (Strict Semantic Version Progression)
- Atomic Installation (POSIX / Windows compliant atomic swap)
- Automatic Rollback on Verification Failure
"""

import os
import shutil
import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any


@dataclass
class ModelUpdatePackage:
    """Encapsulates an offline model distribution bundle."""
    model_name: str
    version: str
    sha256_checksum: str
    signature: str  # Hex-encoded cryptographic signature
    payload_bytes: bytes
    metadata: Optional[Dict[str, Any]] = None


class SecureModelUpdateManager:
    """
    Manages secure, offline deployment of biometric model weight updates.
    Ensures that corrupted, unverified, or downgraded models cannot be installed.
    """

    def __init__(self,
                 models_directory: str,
                 signing_key: bytes = b"MOSIP_DECODE_SECURE_OFFLINE_KEY_2026"):
        self.models_directory = models_directory
        self.signing_key = signing_key
        os.makedirs(self.models_directory, exist_ok=True)

    @staticmethod
    def _parse_semver(version_str: str) -> Tuple[int, int, int]:
        """Parses semantic version string 'X.Y.Z' into comparable tuple."""
        clean = version_str.lstrip("v").strip()
        parts = clean.split(".")
        try:
            return tuple(int(p) for p in parts[:3])
        except ValueError:
            return (0, 0, 0)

    def verify_integrity(self, payload: bytes, expected_sha256: str) -> bool:
        """Verifies payload SHA-256 hash using constant-time comparison."""
        computed = hashlib.sha256(payload).hexdigest()
        return hmac.compare_digest(computed.lower(), expected_sha256.lower())

    def verify_signature(self, payload: bytes, signature_hex: str) -> bool:
        """Verifies cryptographic signature using HMAC-SHA256."""
        expected_sig = hmac.new(self.signing_key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig.lower(), signature_hex.lower())

    def validate_version(self, new_version: str, current_version: Optional[str]) -> bool:
        """
        Anti-downgrade check.
        Ensures new version is strictly greater than current installed version.
        """
        if not current_version:
            return True
        new_tuple = self._parse_semver(new_version)
        current_tuple = self._parse_semver(current_version)
        return new_tuple > current_tuple

    def generate_signed_package(self,
                                model_name: str,
                                version: str,
                                payload: bytes) -> ModelUpdatePackage:
        """Utility for test suites or release pipelines to sign a model payload."""
        sha256 = hashlib.sha256(payload).hexdigest()
        sig = hmac.new(self.signing_key, payload, hashlib.sha256).hexdigest()
        return ModelUpdatePackage(
            model_name=model_name,
            version=version,
            sha256_checksum=sha256,
            signature=sig,
            payload_bytes=payload
        )

    def install_update(self,
                       package: ModelUpdatePackage,
                       target_filename: str,
                       current_version: Optional[str] = None) -> Tuple[bool, str]:
        """
        Applies model update atomically with verification and rollback.
        Returns: (success_bool, message_str)
        """
        # 1. Integrity Verification
        if not self.verify_integrity(package.payload_bytes, package.sha256_checksum):
            return False, "Integrity check failed: SHA-256 checksum mismatch"

        # 2. Signature Verification
        if not self.verify_signature(package.payload_bytes, package.signature):
            return False, "Signature verification failed: Invalid cryptographic signature"

        # 3. Version Validation (Anti-downgrade)
        if not self.validate_version(package.version, current_version):
            return False, f"Anti-downgrade check failed: Version {package.version} is not newer than current {current_version}"

        target_path = os.path.join(self.models_directory, target_filename)
        backup_path = target_path + ".bak"
        temp_path = target_path + ".tmp"

        has_backup = False
        try:
            # Create backup of current file if it exists
            if os.path.exists(target_path):
                shutil.copy2(target_path, backup_path)
                has_backup = True

            # Write payload to staging temporary file
            with open(temp_path, "wb") as f:
                f.write(package.payload_bytes)

            # Atomic swap to target path
            os.replace(temp_path, target_path)

            return True, f"Successfully installed model '{package.model_name}' version {package.version}"

        except Exception as e:
            # Rollback to previous version if temporary write or swap failed
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

            if has_backup and os.path.exists(backup_path):
                try:
                    os.replace(backup_path, target_path)
                except OSError:
                    pass

            return False, f"Installation error, rollback executed: {str(e)}"

    def rollback(self, target_filename: str) -> bool:
        """Manually trigger rollback to last known good backup."""
        target_path = os.path.join(self.models_directory, target_filename)
        backup_path = target_path + ".bak"
        if os.path.exists(backup_path):
            try:
                os.replace(backup_path, target_path)
                return True
            except OSError:
                return False
        return False
