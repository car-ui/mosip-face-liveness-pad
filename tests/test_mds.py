import pytest
from fastapi.testclient import TestClient
from src.mds.mds_server import app, pipeline, device
from src.devices.base import MockScenario
from src.devices.mock_l0_device import MockL0Device
import src.mds.mds_server as mds_module


@pytest.fixture(scope="module")
def client():
    # Ensure client uses Mock device for predictable testing
    mds_module.device = MockL0Device(scenario=MockScenario.BONA_FIDE_LIVE)
    mds_module.device.connect()
    with TestClient(app) as test_client:
        yield test_client
    mds_module.device.disconnect()


def test_mds_info_endpoint(client):
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    
    assert "deviceId" in data
    assert "deviceStatus" in data
    assert "certification" in data
    assert "securityLevel" in data
    assert "vendor" in data
    assert "model" in data
    assert "supportedCaptureModes" in data
    assert "supportedResolutions" in data
    assert "serviceVersion" in data
    assert "livenessCapability" in data
    assert data["livenessCapability"]["passivePAD"] is True
    assert "activeChallenges" in data["livenessCapability"]


def test_mds_switch_device_endpoint(client):
    response = client.post("/switch-device", json={
        "device_mode": "MOCK",
        "scenario": "STATIC_PHOTO_ATTACK"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "MOCK" in data["current_device"]


def test_mds_switch_to_vendor_l1(client):
    response = client.post("/switch-device", json={
        "device_mode": "L1"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "DEV-L1" in data["current_device"]

    info = client.get("/info").json()
    assert info["certification"] == "L1"
    assert info["securityLevel"] == "L1_SECURE_HARDWARE"
    assert info["vendor"] == "GenericMOSIP_Vendor"


def test_mds_configure_endpoint(client):
    response = client.post("/configure", json={
        "passive_threshold": 0.85,
        "min_challenges": 2,
        "challenge_timeout": 8.0,
        "max_retries": 3,
        "pad_mode": "HEURISTIC"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["configured_policy"]["passive_threshold"] == 0.85
    assert data["configured_policy"]["min_challenges"] == 2


def test_mds_capture_invalid_workflow(client):
    response = client.post("/capture", json={
        "workflow": "INVALID_WORKFLOW_NAME",
        "timeout_seconds": 5
    })
    assert response.status_code == 400


def test_mds_capture_live_success(client):
    # Set mock scenario to live face and configure fast passive pass
    mds_module.device = MockL0Device(scenario=MockScenario.BONA_FIDE_LIVE)
    mds_module.device.connect()
    mds_module.pipeline.policy.passive_threshold = 0.50

    response = client.post("/capture", json={
        "workflow": "RESIDENT_REGISTRATION",
        "resident_id": "RES-00777",
        "timeout_seconds": 10
    })
    assert response.status_code == 200
    data = response.json()
    assert data["responseStatus"] == "SUCCESS"
    assert data["decision"] == "PASSED"
    assert data["residentId"] == "RES-00777"
    assert data["enrollmentStatus"] == "COMPLETED"
    assert len(data["biometrics"]) == 1
    assert data["biometrics"][0]["specVersion"] == "ISO_19794_5"
    assert "tokenHash" in data["biometrics"][0]
    assert len(data["biometrics"][0]["tokenHash"]) == 64
    assert data["biometrics"][0]["livenessVerified"] is True
    assert len(data["biometrics"][0]["data"]) > 100
    assert "modelProvenance" in data["telemetry"]


def test_mds_capture_timeout(client):
    # Empty background scenario (NO_FACE) with short timeout
    mds_module.device = MockL0Device(scenario=MockScenario.NO_FACE)
    mds_module.device.connect()

    response = client.post("/capture", json={
        "workflow": "RESIDENT_REGISTRATION",
        "timeout_seconds": 2
    })
    # Returns 408 Request Timeout
    assert response.status_code == 408
    data = response.json()
    assert data["responseStatus"] == "TIMEOUT"
