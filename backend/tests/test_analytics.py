"""Caregiver dashboard regression checks for privacy, normalization and export."""
import os
import sys
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import Base, engine, SessionLocal
from app.main import app, hash_password
from app.models import QuestionEvent, User, utc_now


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def auth(client, email):
    with SessionLocal() as db:
        db.add(User(email=email, password_hash=hash_password('safe-password'), name='Tester'))
        db.commit()
    response = client.post('/api/login', json={'email': email, 'password': 'safe-password'})
    assert response.status_code == 200
    return {'Authorization': f'Bearer {response.json()["token"]}'}


def test_analytics_normalized_frequency_and_period(client):
    headers = auth(client, 'analytics@test.local')
    for text, source in [('Where are my keys?', 'typed'), ('where ARE my keys!!', 'voice'),
                         ('Who is Alex?', 'quick'), ('What about now?', 'typed')]:
        response = client.post('/api/question', json={'question': text, 'source': source}, headers=headers)
        assert response.status_code == 200, response.text
    data = client.get('/api/caregiver/analytics?days=30', headers=headers).json()
    assert data['total_questions'] == 4
    assert data['unique_questions'] == 3
    assert data['most_asked_question']['count'] == 2
    assert data['most_asked_question']['question'] == 'where ARE my keys!!'
    assert data['answered_questions'] + data['unanswered_questions'] == 4
    assert len(data['recent_questions']) == 4
    assert {e['source'] for e in data['recent_questions']} == {'typed', 'voice', 'quick'}
    with SessionLocal() as db:
        one = db.query(QuestionEvent).order_by(QuestionEvent.id.desc()).first()
        one.created_at = utc_now() - timedelta(days=50)
        db.commit()
    assert client.get('/api/caregiver/analytics?days=7', headers=headers).json()['total_questions'] == 3
    assert client.get('/api/caregiver/analytics?days=0', headers=headers).json()['total_questions'] == 4
    assert client.get('/api/caregiver/analytics?days=8', headers=headers).status_code == 422


def test_account_isolation_csv_protection_and_erase(client):
    one = auth(client, 'first@test.local')
    two = auth(client, 'second@test.local')
    assert client.post('/api/question', json={'question': '=HYPERLINK("bad")'}, headers=one).status_code == 200
    assert client.post('/api/question', json={'question': 'Who is Alex?'}, headers=two).status_code == 200
    assert client.get('/api/caregiver/analytics', headers=one).json()['total_questions'] == 1
    assert client.get('/api/caregiver/analytics', headers=two).json()['total_questions'] == 1
    assert client.get('/api/caregiver/analytics').status_code == 401
    export = client.get('/api/caregiver/questions.csv', headers=one)
    assert export.status_code == 200
    assert "'=HYPERLINK" in export.text
    assert 'Who is Alex?' not in export.text
    assert client.delete('/api/caregiver/questions', headers=one).json()['deleted'] == 1
    assert client.get('/api/caregiver/analytics', headers=one).json()['total_questions'] == 0
    assert client.get('/api/caregiver/analytics', headers=two).json()['total_questions'] == 1


def test_blank_or_very_long_question_not_logged(client):
    headers = auth(client, 'short@test.local')
    assert client.post('/api/question', json={'question': '  '}, headers=headers).status_code == 422
    assert client.post('/api/question', json={'question': 'a'*501}, headers=headers).status_code == 422
    assert client.get('/api/caregiver/analytics', headers=headers).json()['total_questions'] == 0
