import pytest
import os
import tempfile
import hashlib
from src.core.model_updater import SecureModelUpdateManager, ModelUpdatePackage


def test_model_updater_integrity_verification():
    with tempfile.TemporaryDirectory() as tmpdir:
        updater = SecureModelUpdateManager(models_directory=tmpdir)
        payload = b"FAKE_ONNX_MODEL_BINARY_DATA_V1"
        sha256 = hashlib.sha256(payload).hexdigest()

        assert updater.verify_integrity(payload, sha256) is True
        assert updater.verify_integrity(payload, "0000000000000000000000000000000000000000000000000000000000000000") is False


def test_model_updater_signature_verification():
    with tempfile.TemporaryDirectory() as tmpdir:
        key = b"TEST_SIGNING_KEY_123"
        updater = SecureModelUpdateManager(models_directory=tmpdir, signing_key=key)
        payload = b"SECURE_MODEL_DATA_PAYLOAD"

        package = updater.generate_signed_package("model_anti_spoof", "2.0.0", payload)
        assert updater.verify_signature(payload, package.signature) is True
        assert updater.verify_signature(payload, "deadbeef" * 8) is False


def test_model_updater_version_anti_downgrade():
    with tempfile.TemporaryDirectory() as tmpdir:
        updater = SecureModelUpdateManager(models_directory=tmpdir)

        # 2.0.0 is newer than 1.0.0
        assert updater.validate_version("2.0.0", "1.0.0") is True
        assert updater.validate_version("2.1.0", "2.0.5") is True

        # Downgrade rejected
        assert updater.validate_version("1.0.0", "2.0.0") is False
        assert updater.validate_version("1.5.0", "1.5.0") is False


def test_model_updater_atomic_install_and_rollback():
    with tempfile.TemporaryDirectory() as tmpdir:
        updater = SecureModelUpdateManager(models_directory=tmpdir)
        target_name = "anti_spoof_v1.onnx"
        initial_payload = b"INITIAL_MODEL_DATA_VERSION_1"
        updated_payload = b"UPDATED_MODEL_DATA_VERSION_2"

        # Install initial version 1.0.0
        pkg_v1 = updater.generate_signed_package("anti_spoof", "1.0.0", initial_payload)
        ok, msg = updater.install_update(pkg_v1, target_name, current_version=None)
        assert ok is True
        installed_path = os.path.join(tmpdir, target_name)
        assert os.path.exists(installed_path)
        with open(installed_path, "rb") as f:
            assert f.read() == initial_payload

        # Install updated version 2.0.0
        pkg_v2 = updater.generate_signed_package("anti_spoof", "2.0.0", updated_payload)
        ok, msg = updater.install_update(pkg_v2, target_name, current_version="1.0.0")
        assert ok is True
        with open(installed_path, "rb") as f:
            assert f.read() == updated_payload

        # Corrupted update attempted (bad checksum)
        corrupted_pkg = ModelUpdatePackage(
            model_name="anti_spoof",
            version="3.0.0",
            sha256_checksum="invalid_checksum",
            signature="invalid_sig",
            payload_bytes=b"CORRUPTED_BYTES"
        )
        ok, msg = updater.install_update(corrupted_pkg, target_name, current_version="2.0.0")
        assert ok is False
        assert "Integrity check failed" in msg
        # Target remains intact at version 2
        with open(installed_path, "rb") as f:
            assert f.read() == updated_payload

        # Trigger manual rollback to v1 backup
        rollback_ok = updater.rollback(target_name)
        assert rollback_ok is True
        with open(installed_path, "rb") as f:
            assert f.read() == initial_payload
