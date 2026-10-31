"""Integration and regression tests. Uses only synthetic user data and images."""
import io
import os
import sys
from datetime import datetime, timedelta

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import Base, SessionLocal, engine
from app.main import app, hash_password, verify_password
from app.models import User


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def create_user(email, name='Tester', role='user'):
    with SessionLocal() as db:
        record = User(email=email, password_hash=hash_password('test-pass'), name=name, role=role)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record.id


def token(client, email, password='test-pass'):
    res = client.post('/api/login', json={'email': email, 'password': password})
    assert res.status_code == 200, res.text
    return {'Authorization': 'Bearer ' + res.json()['token']}


def demo(client):
    result = client.post('/api/seed')
    assert result.status_code == 200, result.text
    result = client.post('/api/login', json={'email': 'demo@remindai.app', 'password': 'remind123'})
    assert result.status_code == 200, result.text
    return {'Authorization': 'Bearer ' + result.json()['token']}


def test_health_and_demo_login(client):
    assert client.get('/api/health').json()['status'] == 'ok'
    headers = demo(client)
    assert client.get('/api/home', headers=headers).status_code == 200
    assert client.get('/api/home', headers=headers).json()['next_activity'] == 'Lunch with family'
    assert client.get('/api/family-members', headers=headers).json()
    assert client.get('/api/seed').status_code == 405  # no accidental GET side effect


def test_personal_data_requires_valid_token(client):
    demo(client)
    for url in ('/api/home', '/api/users', '/api/family-members', '/api/objects', '/api/emergency', '/api/audit'):
        assert client.get(url).status_code == 401, url
    assert client.post('/api/question', json={'question': 'Who is Anu?'}).status_code == 401
    assert client.post('/api/detect-person', files={'frame': ('a.jpg', b'fake', 'image/jpeg')}).status_code == 401
    assert client.get('/api/home', headers={'Authorization':'Bearer junk'}).status_code == 401


def test_users_only_access_their_own_records(client):
    id_a = create_user('alice@example.com')
    id_b = create_user('bob@example.com', role='caregiver')
    h_a = token(client, 'alice@example.com')
    h_b = token(client, 'bob@example.com')
    assert client.get('/api/home', headers=h_a).json()['user']['id'] == id_a
    assert client.get('/api/home', headers=h_b).json()['user']['id'] == id_b
    assert client.get('/api/objects', params={'user_id':id_b}, headers=h_a).status_code == 403
    assert client.get('/api/family-members', params={'user_id':id_a}, headers=h_b).status_code == 403
    assert client.get('/api/users', headers=h_a).json()[0]['id'] == id_a


def test_record_create_edit_delete_and_tenant_isolation(client):
    first = create_user('one@example.com')
    second = create_user('two@example.com')
    h1=token(client,'one@example.com');h2=token(client,'two@example.com')
    new = client.post('/api/objects', headers=h1, json={'name':'umbrella','last_location':'hall closet'})
    assert new.status_code == 200, new.text
    object_id=new.json()['id']
    assert client.get('/api/objects', headers=h2).json() == []
    assert client.put(f'/api/objects/{object_id}', headers=h2, json={'name':'changed','last_location':'drawer'}).status_code == 404
    assert client.delete(f'/api/objects/{object_id}', headers=h2).status_code == 404
    assert client.put(f'/api/objects/{object_id}', headers=h1, json={'name':'umbrella','last_location':'front door'}).json()['last_location'] == 'front door'
    assert client.delete(f'/api/objects/{object_id}', headers=h1).status_code == 200
    assert not client.get('/api/objects', headers=h1).json()


def test_family_member_delete_detaches_memories(client):
    headers=demo(client)
    members=client.get('/api/family-members', headers=headers).json()
    memory=client.get('/api/memories',headers=headers).json()[0]
    anu=next(member for member in members if member['name']=='Anu')
    assert memory['person_id']==anu['id']
    assert client.delete(f"/api/family-members/{anu['id']}", headers=headers).status_code == 200
    assert client.get('/api/memories', headers=headers).json()[0]['person_id'] is None


def test_cannot_link_other_users_profile_to_memory(client):
    create_user('one@example.com');create_user('two@example.com')
    h1=token(client,'one@example.com');h2=token(client,'two@example.com')
    member=client.post('/api/family-members',headers=h1,json={'name':'Caregiver','relationship':'friend'}).json()
    response=client.post('/api/memories',headers=h2,json={'title':'wrong link','person_id':member['id']})
    assert response.status_code == 422, response.text


def test_questions_use_approved_profiles_and_saved_object_names(client):
    headers=demo(client)
    who=client.post('/api/question',headers=headers,json={'question':'Who is Anu?'}).json()
    assert who['category']=='person' and 'Anu' in who['answer']
    created=client.post('/api/objects',headers=headers,json={'name':'umbrella','last_location':'front porch'})
    assert created.status_code == 200
    obj=client.post('/api/question',headers=headers,json={'question':'Where is my umbrella?'}).json()
    assert obj['category']=='object' and 'front porch' in obj['answer']
    generic=client.post('/api/question',headers=headers,json={'question':'What is the capital of Jupiter?'}).json()
    assert generic['confidence']=='low'
    assert 'saved' in generic['answer']
    upcoming=client.post('/api/question',headers=headers,json={'question':'next activity'}).json()
    assert upcoming['category']=='schedule'
    assert 'Lunch with family' in upcoming['answer']


def _jpeg(image):
    ok, encoded=cv2.imencode('.jpg',image)
    assert ok
    return encoded.tobytes()


def test_face_endpoint_rejects_bad_inputs(client):
    headers=demo(client)
    assert client.post('/api/detect-person',headers=headers,files={'frame':('x.txt',b'data','text/plain')}).status_code == 415
    assert client.post('/api/detect-person',headers=headers,files={'frame':('x.jpg',b'not-an-image','image/jpeg')}).status_code == 400
    assert client.post('/api/detect-person',headers=headers,files={'frame':('x.jpg',b'x'*(5*1024*1024+1),'image/jpeg')}).status_code == 413
    blank=np.zeros((360,480,3),dtype=np.uint8)
    result=client.post('/api/detect-person',headers=headers,files={'frame':('x.jpg',_jpeg(blank),'image/jpeg')})
    assert result.status_code==200,result.text
    assert result.json()['face_detected'] is False
    assert result.json()['face_count']==0
    assert result.json()['identifies_person'] is False


def test_face_endpoint_on_synthetic_face_and_boxes(client):
    headers=demo(client)
    photo=np.zeros((420,420,3),dtype=np.uint8)
    cv2.ellipse(photo,(210,190),(95,110),0,0,360,(220,180,150),-1)
    cv2.circle(photo,(170,165),16,(20,20,20),-1)
    cv2.circle(photo,(250,165),16,(20,20,20),-1)
    cv2.rectangle(photo,(160,240),(260,275),(30,30,30),-1)
    result=client.post('/api/detect-person',headers=headers,files={'frame':('face.jpg',_jpeg(photo),'image/jpeg')})
    assert result.status_code==200,result.text
    data=result.json()
    assert data['face_count']>=1
    assert data['detector'] in ('haar','yunet')
    assert all(0<=box[key]<=1 for box in data['faces'] for key in ('x','y','width','height'))


def test_password_and_evaluation_not_fake(client):
    hashed=hash_password('hello')
    assert verify_password('hello',hashed)
    assert not verify_password('wrong',hashed)
    assert client.get('/api/evaluation').json()['status']=='not_benchmarked'
