"""API contract tests. Accepted captures use an explicit inference test double."""
import asyncio
import base64
import hashlib
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from src.core.config import PADMode, PADVerdict, WorkflowType
from src.core.pipeline import PipelineState, PipelineStepResult, LivenessDecision
from src.devices.base import MockScenario
from src.devices.mock_l0_device import MockL0Device
import src.mds.mds_server as mds


@pytest.fixture
def client(controlled_pipeline, monkeypatch):
    monkeypatch.setattr(mds, "device", MockL0Device())
    monkeypatch.setattr(mds, "pipeline", controlled_pipeline)
    with TestClient(mds.app, headers={"Authorization": "Bearer " + mds.API_TOKEN}) as c:
        yield c


def test_device_reports_simulation_and_no_certification(client):
    data = client.get('/info').json()
    assert data['simulation'] is True
    assert data['certification'] == 'NOT_CERTIFIED'
    assert data['nativeMosipIntegrationVerified'] is False
    assert data['livenessCapability']['hardwareLiveness'] is False


def test_mds_capture_payload_hash_and_ephemeral_cleanup(client):
    r = client.post('/capture', json={'resident_id':'TEST-001', 'timeout_seconds':5})
    assert r.status_code == 200
    d = r.json()
    assert d['responseStatus'] == 'SUCCESS'
    assert d['simulation'] is True
    assert d['identityMatchPerformed'] is False
    biometric = d['biometrics'][0]
    assert biometric['specVersion'] == 'APPLICATION_JPEG'
    assert hashlib.sha256(base64.b64decode(biometric['data'])).hexdigest() == biometric['tokenHash']
    assert mds.pipeline._captured_biometric is None
    assert mds._latest_jpeg is None
    assert r.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('path,body', [('/capture',{}),('/configure',{}),('/switch-device',{})])
def test_mutations_require_token(client,path,body):
    assert client.post(path,json=body,headers={'Authorization':'Bearer wrong'}).status_code == 401


def test_cross_origin_and_rebinding_blocked(client):
    assert client.post('/capture',json={},headers={'Origin':'https://attacker.example'}).status_code == 403
    assert client.get('/info',headers={'Host':'attacker.example'}).status_code == 400


def test_busy_capture_rejects_mutations(client):
    mds._capture_lock.acquire()
    try:
        for path in ('/capture','/configure','/switch-device'):
            assert client.post(path,json={}).status_code == 409
    finally:
        mds._capture_lock.release()


def test_workflow_configuration_updates_actual_detector_and_survives_capture(client):
    r = client.post('/configure',json={'workflow':'OPERATOR_AUTHENTICATION',
        'passive_threshold':.94,'min_challenges':3,'pad_mode':'ONNX'})
    assert r.status_code == 200
    assert mds.pipeline.pad_detector.mode == PADMode.ONNX_ONLY
    assert mds.pipeline.pad_detector.high_confidence_threshold == .94
    mds.pipeline.set_workflow(WorkflowType.OPERATOR_AUTHENTICATION)
    assert mds.pipeline.policy.min_challenges == 3
    assert mds.pipeline.policy.passive_threshold == .94


def test_invalid_config_is_atomic(client):
    before=mds.pipeline.policy.passive_threshold
    assert client.post('/configure',json={'passive_threshold':.91,'pad_mode':'invalid'}).status_code == 422
    assert mds.pipeline.policy.passive_threshold == before
    assert client.post('/configure',json={'workflow':'OPERATOR_AUTHENTICATION',
        'active_liveness_enabled':False}).status_code == 422
    assert mds.pipeline.config.operator_policy.active_liveness_enabled


@pytest.mark.parametrize('body',[{'device_mode':'unknown'},{'scenario':'TYPO'},{'device_mode':'MOCK','unexpected':1}])
def test_invalid_device_selection_does_not_silently_start_live_mock(client,body):
    assert client.post('/switch-device',json=body).status_code == 422


def test_device_switch_to_l1_is_explicitly_simulated(client):
    assert client.post('/switch-device',json={'device_mode':'L1'}).status_code == 200
    d=client.get('/info').json()
    assert d['securityLevel']=='L1_SIMULATED'
    assert d['simulation'] and d['certification']=='NOT_CERTIFIED'


def test_no_automatic_mock_challenge_completion(client):
    # A high passive score still cannot satisfy mandatory operator actions.
    r=client.post('/capture',json={'workflow':'OPERATOR_AUTHENTICATION','timeout_seconds':2})
    assert r.status_code == 408
    assert r.json()['biometrics']==[]
    assert mds.pipeline.challenge_manager.completed_challenges==[]


def test_disconnect_returns_device_error_without_biometrics(client,monkeypatch):
    monkeypatch.setattr(mds.device,'read_frame',lambda:(False,None))
    r=client.post('/capture',json={})
    assert r.status_code==503 and r.json()['biometrics']==[]
    assert not mds._capture_lock.locked()


def test_attack_response_does_not_expose_diagnostics(client,monkeypatch):
    def reject(frame):
        return PipelineStepResult(PipelineState.ATTACK_REJECTED,LivenessDecision.ATTACK_DETECTED,
                                  'MOIRE_HARMONICS_DETECTED','internal-threshold',0)
    monkeypatch.setattr(mds.pipeline,'process_frame',reject)
    r=client.post('/capture',json={})
    assert r.json()['biometrics']==[]
    assert 'MOIRE' not in r.text and 'internal-threshold' not in r.text


def test_preview_does_not_process_liveness(client,monkeypatch):
    monkeypatch.setattr(mds.pipeline,'process_frame',lambda *a:pytest.fail('preview advanced pipeline'))
    response=mds.stream_frames()
    async def read():
        first=await anext(response.body_iterator)
        await response.body_iterator.aclose()
        return first
    assert b'Content-Type: image/jpeg' in asyncio.run(read())


def test_console_status_and_metrics(client):
    html=client.get('/')
    assert html.status_code==200 and 'aria-live="polite"' in html.text
    assert '__API_TOKEN__' not in html.text
    assert client.get('/status').status_code==200
    assert 'failureRate' in client.get('/metrics').json()


def test_unknown_workflow_rejected(client):
    assert client.post('/capture',json={'workflow':'TYPO'}).status_code==400


def test_disabling_liveness_cannot_issue_verified_biometrics(client):
    assert client.post('/configure',json={'liveness_enabled':False}).status_code==200
    result=client.post('/capture',json={}).json()
    assert result['responseStatus']=='FAILURE'
    assert result['biometrics']==[]


def test_guidance_can_be_configured_without_unknown_states(client):
    assert client.post('/configure',json={'guidance_messages':{'FACE_DETECTION':'Please face the camera.'}}).status_code==200
    assert client.get('/configuration').json()['guidance_messages']['FACE_DETECTION']=='Please face the camera.'
    assert client.post('/configure',json={'guidance_messages':{'TYPO':'Invalid state'}}).status_code==422


def test_reselecting_webcam_reuses_the_open_handle(client,monkeypatch):
    class Camera(MockL0Device):
        created=0
        def __init__(self,*a,**kw):
            super().__init__()
            Camera.created+=1
    camera=Camera()
    camera.connect()
    monkeypatch.setattr(mds,'WebcamCaptureDevice',Camera)
    monkeypatch.setattr(mds,'device',camera)
    assert client.post('/switch-device',json={'device_mode':'WEBCAM'}).status_code==200
    assert mds.device is camera and Camera.created==1


def test_device_exception_returns_safe_failure_and_releases_capture(client,monkeypatch):
    def broken():
        raise RuntimeError('vendor-private-details')
    monkeypatch.setattr(mds.device,'read_frame',broken)
    response=client.post('/capture',json={})
    assert response.status_code==503 and response.json()['biometrics']==[]
    assert 'vendor-private-details' not in response.text
    assert not mds._capture_lock.locked()
