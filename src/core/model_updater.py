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
import json
import re
from pathlib import Path
import threading
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


# Explicitly labeled development/test signing key fixture (NOT for production use)
DEFAULT_DEV_TEST_KEY = b"DEV_INSECURE_TEST_KEY_FOR_LOCAL_EVALUATION_ONLY"


class SecureModelUpdateManager:
    """
    Manages secure, offline deployment of biometric model weight updates.
    Ensures that corrupted, unverified, or downgraded models cannot be installed.
    Production Architecture Note:
    In production MOSIP deployments, model payloads are signed by the MOSIP Root Authority
    using asymmetric PKI (e.g. RSA-4096 / ECDSA P-384) or hardware KMS/HSM modules.
    For offline testing, symmetric HMAC-SHA256 with key injection via environment variable
    MOSIP_MODEL_SIGNING_KEY or explicit parameter is supported.
    """

    def __init__(self,
                 models_directory: str,
                 signing_key: Optional[bytes] = None,
                 allow_insecure_test_key: bool = False,
                 verification_key=None,
                 private_key=None):
        self.models_directory = models_directory
        env_key = os.environ.get("MOSIP_MODEL_SIGNING_KEY")
        if signing_key is not None:
            self.signing_key = signing_key
        elif env_key:
            self.signing_key = env_key.encode("utf-8")
        elif allow_insecure_test_key:
            self.signing_key = DEFAULT_DEV_TEST_KEY
        elif verification_key is not None:
            self.signing_key = None
        else:
            raise ValueError("Supply a signing key or Ed25519 verification key. Development keys require explicit opt-in.")
        self.verification_key = verification_key
        self.private_key = private_key
        self._lock = threading.RLock()

        os.makedirs(self.models_directory, exist_ok=True)

    @staticmethod
    def _parse_semver(version_str: str) -> Tuple[int, int, int]:
        """Parses semantic version string 'X.Y.Z' into comparable tuple."""
        if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version_str):
            raise ValueError("Version must contain exactly three unsigned integers, X.Y.Z")
        return tuple(int(p) for p in version_str.split("."))

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
        try:
            new_tuple = self._parse_semver(new_version)
            return not current_version or new_tuple > self._parse_semver(current_version)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _manifest_bytes(package):
        return json.dumps({"model_name": package.model_name, "version": package.version,
                           "sha256": package.sha256_checksum, "metadata": package.metadata},
                          sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

    def _target(self, filename):
        root = Path(self.models_directory).resolve()
        if not filename or Path(filename).name != filename or "/" in filename or "\\" in filename or ":" in filename:
            raise ValueError("Target must be a filename inside the model directory")
        target = root / filename
        for candidate in (target, Path(str(target) + ".tmp"), Path(str(target) + ".bak"), Path(str(target) + ".version")):
            if candidate.is_symlink() or candidate.resolve().parent != root:
                raise ValueError("Model paths must stay inside the model directory")
        return str(target)

    def generate_signed_package(self,
                                model_name: str,
                                version: str,
                                payload: bytes) -> ModelUpdatePackage:
        """Utility for test suites or release pipelines to sign a model payload."""
        sha256 = hashlib.sha256(payload).hexdigest()
        package = ModelUpdatePackage(
            model_name=model_name,
            version=version,
            sha256_checksum=sha256,
            signature="",
            payload_bytes=payload
        )
        manifest = self._manifest_bytes(package)
        if self.private_key is not None:
            package.signature = self.private_key.sign(manifest).hex()
        elif self.signing_key is not None:
            package.signature = hmac.new(self.signing_key, manifest, hashlib.sha256).hexdigest()
        else:
            raise ValueError("A verification-only manager cannot sign packages")
        return package

    def install_update(self,
                       package: ModelUpdatePackage,
                       target_filename: str,
                       current_version: Optional[str] = None) -> Tuple[bool, str]:
        """
        Applies model update atomically with verification and rollback.
        Returns: (success_bool, message_str)
        """
        with self._lock:
            return self._install_update(package, target_filename, current_version)

    def _install_update(self, package, target_filename, current_version):
        try:
            target_path = self._target(target_filename)
            manifest = self._manifest_bytes(package)
            version_file = Path(target_path + ".version")
            installed_version = version_file.read_text(encoding="utf-8") if version_file.exists() else None
        except (ValueError, OSError, TypeError):
            return False, "Invalid model path, manifest, or installed version record"
        # 1. Integrity Verification
        if not self.verify_integrity(package.payload_bytes, package.sha256_checksum):
            return False, "Integrity check failed: SHA-256 checksum mismatch"

        # 2. Signature Verification
        try:
            if self.verification_key is not None:
                self.verification_key.verify(bytes.fromhex(package.signature), manifest)
                signature_valid = True
            else:
                signature_valid = self.verify_signature(manifest, package.signature)
        except Exception:
            signature_valid = False
        if not signature_valid:
            return False, "Signature verification failed: Invalid cryptographic signature"

        # 3. Version Validation (Anti-downgrade)
        if (not self.validate_version(package.version, current_version)
                or not self.validate_version(package.version, installed_version)):
            return False, f"Anti-downgrade check failed: Version {package.version} is not newer than current {current_version}"

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
                f.flush()
                os.fsync(f.fileno())

            # Persist the high-water mark before publishing the model. A crash may require
            # operator recovery but cannot permit an older signed package to be replayed.
            version_file.write_text(package.version, encoding="utf-8")

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
        try:
            target_path = self._target(target_filename)
        except ValueError:
            return False
        backup_path = target_path + ".bak"
        if os.path.exists(backup_path):
            try:
                os.replace(backup_path, target_path)
                return True
            except OSError:
                return False
        return False
