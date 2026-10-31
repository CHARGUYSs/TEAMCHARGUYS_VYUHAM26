"""Recognition security and matching tests using synthetic vectors.

Real-world face accuracy cannot be asserted without model weights and labeled faces.
"""
import io
import json
import os
import sys

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import app.main as main
from app import face_identity
from app.database import Base, SessionLocal, engine
from app.main import app, hash_password
from app.models import FaceTemplate, User


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def add_login(client, email):
    with SessionLocal() as db:
        db.add(User(email=email, name=email, password_hash=hash_password('pass'), role='user'))
        db.commit()
    result = client.post('/api/login', json={'email':email, 'password':'pass'})
    assert result.status_code==200
    return {'Authorization':'Bearer '+result.json()['token']}


def photo():
    img = np.zeros((180,180,3),np.uint8)
    _, buffer=cv2.imencode('.jpg',img)
    return {'frame':('demo.jpg',bytes(buffer),'image/jpeg')}


def feature(idx):
    v = np.zeros(128,dtype=np.float32)
    v[idx]=1
    return v


def mock_models(monkeypatch):
    monkeypatch.setattr(main, 'model_status', lambda:{'ready':True,'message':'ready','match_threshold':0.46})
    monkeypatch.setattr(face_identity, '_load_models', lambda:None)
    monkeypatch.setattr(face_identity, '_detector', object())
    monkeypatch.setattr(face_identity, '_recognizer', object())


def test_recognize_unknown_without_enrollment(monkeypatch):
    mock_models(monkeypatch)
    monkeypatch.setattr(face_identity, '_faces_with_features', lambda image:[{'box':{'x':.1,'y':.1,'width':.5,'height':.5},'vector':feature(0)}])
    result=face_identity.recognize(np.zeros((180,180,3),np.uint8), [])
    assert result[0]['status']=='unknown'
    assert result[0]['person_id'] is None
    assert result[0]['similarity'] is None


def test_recognition_matches_enrolled_profile_and_not_other(monkeypatch):
    mock_models(monkeypatch)
    monkeypatch.setattr(face_identity, '_faces_with_features', lambda image:[{'box':{'x':.2,'y':.2,'width':.4,'height':.4},'vector':feature(0)}])
    images = [(1, 'Alex', 'friend', json.dumps(feature(0).tolist())), (2, 'Casey', 'sibling', json.dumps(feature(1).tolist()))]
    r=face_identity.recognize(np.zeros((180,180,3),np.uint8), images)
    assert r[0]['status']=='matched'
    assert r[0]['person_id']==1 and r[0]['name']=='Alex'
    assert r[0]['similarity']==1.0
    monkeypatch.setattr(face_identity, '_faces_with_features', lambda image:[{'box':{'x':.2,'y':.2,'width':.4,'height':.4},'vector':feature(2)}])
    assert face_identity.recognize(np.zeros((180,180,3),np.uint8), images)[0]['status']=='unknown'


def test_margin_prevents_ambiguous_matches(monkeypatch):
    mock_models(monkeypatch)
    monkeypatch.setattr(face_identity, '_faces_with_features', lambda image:[{'box':{'x':.2,'y':.2,'width':.4,'height':.4},'vector':feature(0)}])
    templates=[(1,'Alex','friend',json.dumps(feature(0).tolist())),(2,'Alex2','neighbor',json.dumps(feature(0).tolist()))]
    assert face_identity.recognize(np.zeros((180,180,3),np.uint8), templates)[0]['status']=='unknown'


def test_enroll_api_consent_and_user_separation(monkeypatch, client):
    h1=add_login(client, 'user1@test.local')
    h2=add_login(client, 'user2@test.local')
    member=client.post('/api/family-members', headers=h1, json={'name':'Alex','relationship':'friend'}).json()['id']
    assert client.post(f'/api/family-members/{member}/enroll?consent=true', headers=h2,files=photo()).status_code==404
    assert client.post(f'/api/family-members/{member}/enroll', headers=h1,files=photo()).status_code==422
    monkeypatch.setattr(main, 'extract_enrollment', lambda image:feature(0).tolist())
    result=client.post(f'/api/family-members/{member}/enroll?consent=true',headers=h1,files=photo())
    assert result.status_code==200, result.text
    assert client.get('/api/recognition/status',headers=h1).json()['enrollments'][str(member)]==1
    assert client.get('/api/recognition/status',headers=h2).json()['enrolled_people']==0
    assert client.delete(f'/api/family-members/{member}/enrollment',headers=h2).status_code==404
    assert client.delete(f'/api/family-members/{member}',headers=h1).status_code==200
    with SessionLocal() as db:
        assert db.query(FaceTemplate).count()==0


def test_recognize_api_scopes_enrollments_to_current_user(monkeypatch,client):
    h1=add_login(client,'private1@test.local')
    h2=add_login(client,'private2@test.local')
    member=client.post('/api/family-members',headers=h1,json={'name':'Private Person','relationship':'friend'}).json()['id']
    monkeypatch.setattr(main,'extract_enrollment',lambda image:feature(0).tolist())
    assert client.post(f'/api/family-members/{member}/enroll?consent=true',headers=h1,files=photo()).status_code==200
    mock_models(monkeypatch)
    captures=[]
    def faux_recognize(img, templates):
        captures.append(templates)
        return []
    monkeypatch.setattr(main,'recognize',faux_recognize)
    result=client.post('/api/recognize-person',headers=h2,files=photo())
    assert result.status_code==200,result.text
    assert captures[-1]==[]
    result=client.post('/api/recognize-person',headers=h1,files=photo())
    assert result.status_code==200,result.text
    assert len(captures[-1])==1 and captures[-1][0][1]=='Private Person'
