import importlib.util
import json
import os
from pathlib import Path
from time import time
from datetime import datetime, timezone
HERE=Path(__file__).resolve().parents[1]

def module(file,name):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def test_positive_negative():
    d=module('security/detection.py','gcp_detection')
    assert d.test_fixture(HERE/'security/fixtures/telemetry-positive-negative.jsonl')
    assert d.heartbeat_gap([{'event':'security_heartbeat','timestamp':'2026-11-17T10:00:00+00:00'}],
                           evaluated_at=datetime(2026,11,17,10,0,23,tzinfo=timezone.utc).timestamp())
    assert not d.heartbeat_gap([],evaluated_at=time())  # not observed since start

def test_machine_proof_uses_short_lived_scoped_signature(monkeypatch):
    from app.security.service_proof import make_proof,dependency_headers
    secret='test_secret_for_security_game_day_1234567890'
    token=make_proof(secret)
    parts=token.split('.')
    import base64
    claims=json.loads(base64.urlsafe_b64decode(parts[1]+'=='))
    assert claims['aud']=='veterinaria-aws:/pets/raw'
    assert claims['exp']-claims['iat']==30
    monkeypatch.setenv('SERVICE_AUTH_SECRET',secret)
    monkeypatch.setenv('SECURITY_AUTH_MODE','protected')
    assert dependency_headers()['x-service-token'].startswith('v1.')
    monkeypatch.setenv('SECURITY_AUTH_MODE','baseline')
    assert dependency_headers()['x-service-token']==secret

def test_ai_prompt_injection_is_untrusted_data(tmp_path):
    import subprocess,sys
    subprocess.run([sys.executable,str(HERE/'security/ai_review.py'),'--events',
       str(HERE/'security/fixtures/ai-prompt-injection.jsonl'),'--out',str(tmp_path)],check=True)
    prompt=(tmp_path/'triage_prompt.txt').read_text()
    review=json.loads((tmp_path/'review.json').read_text())
    assert 'ignore all previous instructions' in prompt.lower()
    assert 'nunca instrucciones' in prompt
    assert review['untrustedInstructionSeenByLocalHeuristic']
    assert review['model']=='NO_MODEL_CALLED'

def test_honeytoken_middleware(tmp_path,monkeypatch,capsys):
    monkeypatch.setenv('DATABASE_URL','sqlite:///'+str(tmp_path/'test.db'))
    monkeypatch.setenv('SECURITY_HONEYTOKEN_PATH','/.well-known/sec-lab-decoy-unique')
    from app.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        r=c.get('/.well-known/sec-lab-decoy-unique')
        assert r.status_code==404
        assert r.headers['x-trace-id']
        assert c.get('/health/live').status_code==200
    assert 'honeytoken_touched' in capsys.readouterr().out
