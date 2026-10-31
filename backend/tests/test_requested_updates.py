"""Feature integration checks: synthetic data, no real patient records."""
from datetime import date, datetime, timedelta
import os
import sys

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import Base, SessionLocal, engine
from app.main import app, hash_password
from app.models import QuestionEvent, QuizAttempt, User, utc_now


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as browser:
        yield browser


def account(client, email):
    with SessionLocal() as db:
        db.add(User(email=email, name='Demo', password_hash=hash_password('test-pass')))
        db.commit()
    result = client.post('/api/login', json={'email':email, 'password':'test-pass'})
    assert result.status_code == 200, result.text
    return {'Authorization': 'Bearer ' + result.json()['token']}


def test_date_sorted_assigned_tasks_and_patient_future_window(client):
    a=account(client,'task-a@local.test'); b=account(client,'task-b@local.test')
    today=date.today()
    dates=[today+timedelta(days=n) for n in (4,0,2)]
    for i,d in enumerate(dates):
        res=client.post('/api/caregiver/daily-tasks', headers=a,
                        json={'title':f'Task {i}', 'task_date':d.isoformat()})
        assert res.status_code==201, res.text
    all_tasks=client.get('/api/caregiver/daily-tasks',headers=a).json()
    assert [t['task_date'] for t in all_tasks] == sorted(d.isoformat() for d in dates)
    visible=client.get('/api/daily-tasks?upcoming_days=14',headers=a).json()
    assert [t['task_date'] for t in visible] == sorted(d.isoformat() for d in dates)
    assert len(client.get('/api/daily-tasks',headers=a).json())==1
    assert client.post(f"/api/daily-tasks/{all_tasks[2]['id']}/complete",headers=a).status_code==409
    assert client.post(f"/api/caregiver/daily-tasks/{all_tasks[2]['id']}/verify",headers=a,
                       json={'status':'verified'}).status_code==409
    achievement=client.get('/api/caregiver/task-achievement',headers=a).json()
    assert achievement['total_tasks']==1  # Future assigned tasks do not lower today's completion rate.
    assert client.get('/api/caregiver/daily-tasks',headers=b).json()==[]
    assert client.get('/api/daily-tasks?upcoming_days=55',headers=a).status_code==422


def test_refresh_uses_new_saved_information_and_preserves_answer_history(client):
    h=account(client,'quiz-a@local.test')
    client.post('/api/family-members',headers=h,json={'name':'Isha','relationship':'daughter'})
    initial=client.get('/api/daily-quiz',headers=h).json()['questions']
    assert len(initial)==3
    first=initial[0]
    answer=client.post(f"/api/daily-quiz/{first['id']}/answer",headers=h,
                       json={'answer':first['options'][0]})
    assert answer.status_code==200,answer.text
    client.post('/api/objects',headers=h,json={'name':'umbrella','last_location':'hall cupboard'})
    updated=client.post('/api/daily-quiz/refresh',headers=h)
    assert updated.status_code==200,updated.text
    assert updated.json()['new_count']>=1
    assert any('umbrella' in q['question_text'] for q in updated.json()['questions'])
    assert all(q['question_text'] not in {q0['question_text'] for q0 in initial} for q in updated.json()['questions'] if q['id'] not in {q0['id'] for q0 in initial})
    stats=client.get('/api/caregiver/quiz-trends',headers=h).json()
    assert stats['answered_questions']==1
    assert stats['tracking_phase_number']==1
    # Repeated fetch does not generate more questions by accident.
    same=client.get('/api/daily-quiz',headers=h).json()['questions']
    assert [q['id'] for q in same]==[q['id'] for q in updated.json()['questions']]


def test_media_private_upload_fetch_delete_and_mime_guard(client):
    a=account(client,'media-a@local.test');b=account(client,'media-b@local.test')
    made=client.post('/api/memories',headers=a,json={'title':'Family picnic'})
    assert made.status_code==200,made.text
    mid=made.json()['id']
    assert made.json()['media']==[]
    ok,img=cv2.imencode('.png',np.zeros((24,24,3),dtype=np.uint8)); assert ok
    payload=img.tobytes()
    uploaded=client.post(f'/api/memories/{mid}/media',headers=a,
                         files={'file':('pic.png',payload,'image/png')})
    assert uploaded.status_code==201,uploaded.text
    file_id=uploaded.json()['id']
    memories=client.get('/api/memories',headers=a).json()
    assert memories[0]['media'][0]['id']==file_id
    assert client.get(f'/api/memories/media/{file_id}',headers=a).content==payload
    assert client.get(f'/api/memories/media/{file_id}').status_code==401
    assert client.get(f'/api/memories/media/{file_id}',headers=b).status_code==404
    assert client.post(f'/api/memories/{mid}/media',headers=b,
                       files={'file':('intrude.png',payload,'image/png')}).status_code==404
    assert client.delete(f'/api/memories/media/{file_id}',headers=b).status_code==404
    invalid=client.post(f'/api/memories/{mid}/media',headers=a,
                        files={'file':('bad.png',b'<script>bad</script>','image/png')})
    assert invalid.status_code==415
    too_large=client.post(f'/api/memories/{mid}/media',headers=a,
                          files={'file':('large.jpg',b'\xff\xd8\xff'+b'0'*(8*1024*1024),'image/jpeg')})
    assert too_large.status_code==413
    video=client.post(f'/api/memories/{mid}/media',headers=a,
                      files={'file':('clip.webm',b'\x1a\x45\xdf\xa3'+b'fake-video-for-format-test','video/webm')})
    assert video.status_code==201,video.text
    assert client.get(f"/api/memories/media/{video.json()['id']}",headers=a).status_code==200
    assert client.delete(f'/api/memories/{mid}',headers=a).status_code==200
    assert client.get(f'/api/memories/media/{file_id}',headers=a).status_code==404
    assert client.get(f"/api/memories/media/{video.json()['id']}",headers=a).status_code==404


def test_home_next_item_sorts_reminders_and_schedules_together(client):
    h=account(client,'order-a@local.test')
    now=datetime.now().replace(second=0,microsecond=0)
    late=now+timedelta(days=3)
    early=now+timedelta(days=1)
    client.post('/api/schedule',headers=h,json={'title':'Late meeting','scheduled_for':late.isoformat()})
    client.post('/api/reminders',headers=h,json={'title':'Earlier reminder','reminder_time':early.isoformat()})
    result=client.get('/api/home',headers=h).json()
    assert result['next_upcoming']['title']=='Earlier reminder'
    assert result['upcoming_items'][0]['at'] < result['upcoming_items'][1]['at']


def test_data_coverage_phase_never_labels_clinical_stage(client):
    h=account(client,'phase-a@local.test')
    low=client.get('/api/caregiver/quiz-trends',headers=h).json()
    assert low['tracking_phase_number']==1 and low['questions_asked']==0
    with SessionLocal() as db:
        me=db.query(User).filter_by(email='phase-a@local.test').one()
        for ix in range(16):
            db.add(QuizAttempt(user_id=me.id,quiz_date=(date.today()-timedelta(days=ix%4)).isoformat(),
                               question_type='orientation',question_text=f'Which month? {ix}',
                               options='["October", "May"]',correct_answer='October',
                               patient_answer='October',is_correct=True,answered_at=utc_now()))
        for ix in range(10):
            db.add(QuestionEvent(user_id=me.id,question=f'Question {ix}',normalized=f'question {ix}',
                                 category='general',answered=False,source='typed'))
        db.commit()
    stats=client.get('/api/caregiver/quiz-trends?days=30',headers=h).json()
    assert stats['tracking_phase_number']==3
    assert stats['answered_questions']==16 and stats['questions_asked']==10
    assert 'NOT better or worse' in stats['phase_explanation']
