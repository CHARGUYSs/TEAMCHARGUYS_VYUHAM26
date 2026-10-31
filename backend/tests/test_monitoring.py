"""Real activity logging: object requests, caregiver notes, account isolation and deletion."""
import os
import sys
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import Base, SessionLocal, engine
from app.main import app, hash_password
from app.models import ObjectInquiry, ObjectRecord, User, utc_now


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as browser:
        yield browser


def user(client, email):
    with SessionLocal() as db:
        db.add(User(email=email, name='Demo', password_hash=hash_password('secure-password')))
        db.commit()
    result = client.post('/api/login', json={'email': email, 'password': 'secure-password'})
    assert result.status_code == 200
    return {'Authorization': 'Bearer ' + result.json()['token']}


def test_object_from_question_tracks_known_and_unknown(client):
    headers = user(client, 'activity1@local.test')
    with SessionLocal() as db:
        me = db.query(User).filter_by(email='activity1@local.test').first()
        db.add(ObjectRecord(user_id=me.id, name='pen', last_location='desk organizer'))
        db.commit()
    for text in ['Where is my pen?', 'Where is my pen?', 'Where is my wallet?']:
        res = client.post('/api/question', headers=headers, json={'question': text})
        assert res.status_code == 200, res.text
    analytics = client.get('/api/caregiver/monitoring?days=30', headers=headers).json()
    assert analytics['question_count'] == 3
    assert analytics['object_request_count'] == 3
    assert analytics['unique_objects'] == 2
    assert analytics['unresolved_object_requests'] == 1
    assert analytics['top_objects'][0] == {'name': 'pen', 'count': 2}
    assert analytics['recent_objects'][0]['name'] == 'wallet'
    assert analytics['recent_objects'][0]['resolved'] is False
    assert analytics['needs_attention']
    assert analytics['timeline'][0]['kind'] in ('object', 'question')
    assert all('at' in i for i in analytics['timeline'])
    assert analytics['daily_activity'][-1]['objects'] == 3


def test_direct_lookups_saved_or_missing_and_owner_isolation(client):
    owner = user(client, 'first-activity@local.test')
    other = user(client, 'other-activity@local.test')
    with SessionLocal() as db:
        me = db.query(User).filter_by(email='first-activity@local.test').first()
        db.add(ObjectRecord(user_id=me.id, name='Blue pen', last_location='kitchen drawer'))
        db.commit()
    known = client.post('/api/object-lookup', headers=owner, json={'name':'blue PEN'})
    assert known.status_code == 200
    assert known.json()['found'] is True
    assert 'kitchen drawer' in known.json()['answer']
    missed = client.post('/api/object-lookup', headers=other, json={'name':'Blue pen'})
    assert missed.status_code == 200
    assert missed.json()['found'] is False
    assert 'kitchen drawer' not in missed.json()['answer']
    assert client.get('/api/caregiver/monitoring', headers=owner).json()['object_request_count'] == 1
    assert client.get('/api/caregiver/monitoring', headers=other).json()['object_request_count'] == 1
    assert client.get('/api/caregiver/monitoring').status_code == 401
    assert client.post('/api/object-lookup', json={'name':'pen'}).status_code == 401


def test_caregiver_notes_private_and_deletable(client):
    one = user(client,'notes-a@local.test')
    two = user(client,'notes-b@local.test')
    note = client.post('/api/caregiver/notes', headers=one, json={'text':'Please check the desk organizer.'})
    assert note.status_code == 201
    note_id = note.json()['id']
    assert client.get('/api/caregiver/monitoring', headers=one).json()['notes'][0]['text'].startswith('Please')
    assert not client.get('/api/caregiver/monitoring', headers=two).json()['notes']
    assert client.delete(f'/api/caregiver/notes/{note_id}', headers=two).status_code == 404
    assert client.delete(f'/api/caregiver/notes/{note_id}', headers=one).status_code == 200
    assert not client.get('/api/caregiver/monitoring', headers=one).json()['notes']
    assert client.post('/api/caregiver/notes', headers=one, json={'text':'   '}).status_code == 422


def test_filter_export_and_clear_object_history(client):
    one = user(client,'clear-a@local.test')
    two = user(client,'clear-b@local.test')
    client.post('/api/object-lookup', headers=one, json={'name':'pen'})
    client.post('/api/object-lookup', headers=two, json={'name':'keys'})
    with SessionLocal() as db:
        event = db.query(ObjectInquiry).filter_by(object_name='pen').first()
        event.created_at = utc_now() - timedelta(days=45)
        db.commit()
    assert client.get('/api/caregiver/monitoring?days=7', headers=one).json()['object_request_count'] == 0
    assert client.get('/api/caregiver/monitoring?days=0', headers=one).json()['object_request_count'] == 1
    assert client.get('/api/caregiver/monitoring?days=22', headers=one).status_code == 422
    assert 'pen' in client.get('/api/caregiver/monitoring.csv?days=0', headers=one).text
    assert 'keys' not in client.get('/api/caregiver/monitoring.csv?days=0', headers=one).text
    erased = client.delete('/api/caregiver/object-lookups', headers=one).json()
    assert erased['deleted'] == 1
    assert client.get('/api/caregiver/monitoring', headers=one).json()['object_request_count'] == 0
    assert client.get('/api/caregiver/monitoring', headers=two).json()['object_request_count'] == 1


def test_identity_prompt_is_opt_in_and_requires_enrollment(client):
    from app.models import FaceTemplate, FamilyMember
    first = user(client, 'identity-a@local.test')
    second = user(client, 'identity-b@local.test')
    with SessionLocal() as db:
        me = db.query(User).filter_by(email='identity-a@local.test').first()
        member = FamilyMember(user_id=me.id, name='Anu', relationship='daughter')
        db.add(member)
        db.commit()
        member_id = member.id
    data = {'family_member_id':member_id}
    assert client.post('/api/identity-reminder', headers=second, json=data).status_code == 404
    assert client.post('/api/identity-reminder', headers=first, json=data).status_code == 422
    with SessionLocal() as db:
        db.add(FaceTemplate(user_id=db.query(User).filter_by(email='identity-a@local.test').first().id,
                            family_member_id=member_id, embedding='[]'))
        db.commit()
    response = client.post('/api/identity-reminder', headers=first, json=data)
    assert response.status_code == 201
    monitoring = client.get('/api/caregiver/monitoring', headers=first).json()
    assert monitoring['saved_identity_prompts'] == 1
    assert monitoring['recent_people'][0]['name'] == 'Anu'
    assert client.get('/api/caregiver/monitoring', headers=second).json()['saved_identity_prompts'] == 0
    assert client.delete('/api/caregiver/identity-reminders', headers=second).json()['deleted'] == 0
    assert client.delete('/api/caregiver/identity-reminders', headers=first).json()['deleted'] == 1
