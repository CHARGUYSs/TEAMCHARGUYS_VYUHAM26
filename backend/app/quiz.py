"""Daily memory check-in: short, personalized multiple-choice questions built only from
a patient's own saved records (approved family profiles, saved object locations, today's
date). This is NOT a clinical or diagnostic cognitive test — it is a lightweight usage
feature so caregivers can see simple recall trends over time.
"""
import json
import random
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from .models import FamilyMember, ObjectRecord, QuizAttempt, utc_now

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def _options(correct: str, pool: list, count: int = 4) -> list:
    """Distinct, shuffled answers; never show duplicate answer buttons."""
    unique = []
    seen = {correct.casefold()}
    for option in pool:
        text = str(option).strip()
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            unique.append(text)
    random.shuffle(unique)
    choices = [correct] + unique[:max(0, count - 1)]
    random.shuffle(choices)
    return choices


def _person_question(members: list) -> Optional[dict]:
    candidates = [m for m in members if m.approved and m.name.strip()]
    if len(candidates) < 1:
        return None
    target = random.choice(candidates)
    relationship = target.relationship.strip() or "family member"
    pool = [m.relationship.strip() for m in candidates if m.relationship.strip()] + [
        "neighbor", "friend", "doctor", "caregiver",
    ]
    return {
        "question_type": "person",
        "question_text": f"What is {target.name.strip()}'s relationship to you?",
        "options": _options(relationship, pool),
        "correct_answer": relationship,
    }


def _object_question(objects: list) -> Optional[dict]:
    candidates = [o for o in objects if o.name.strip() and o.last_location.strip()]
    if len(candidates) < 1:
        return None
    target = random.choice(candidates)
    pool = [o.last_location.strip() for o in candidates if o.last_location.strip()] + [
        "kitchen counter", "front door", "bedroom table", "living room",
    ]
    return {
        "question_type": "object",
        "question_text": f"Where is your {target.name.strip()} usually kept?",
        "options": _options(target.last_location.strip(), pool),
        "correct_answer": target.last_location.strip(),
    }


def _orientation_question(kind=None) -> dict:
    today = date.today()
    weekday = WEEKDAYS[today.weekday()]
    kind = kind or random.choice(['weekday', 'month', 'year'])
    if kind == 'weekday':
        return {
            'question_type': 'orientation', 'question_text': 'What day of the week is it today?',
            'options': _options(weekday, WEEKDAYS), 'correct_answer': weekday,
        }
    if kind == 'month':
        month = MONTHS[today.month - 1]
        return {
            'question_type': 'orientation', 'question_text': 'What month is it right now?',
            'options': _options(month, MONTHS), 'correct_answer': month,
        }
    year = str(today.year)
    return {
        'question_type': 'orientation', 'question_text': 'What year is it right now?',
        'options': _options(year, [str(today.year + shift) for shift in (-2, -1, 1, 2)]),
        'correct_answer': year,
    }


def _question_pool(db: Session, user_id: int) -> list:
    """Ground every possible answer in the owner's current approved data or the date."""
    members = db.query(FamilyMember).filter(
        FamilyMember.user_id == user_id, FamilyMember.approved.is_(True),
    ).all()
    objects = db.query(ObjectRecord).filter(ObjectRecord.user_id == user_id).all()
    person_questions = []
    for person in members:
        if person.name.strip() and person.relationship.strip():
            relation = person.relationship.strip()
            person_questions.append({
                'question_type': 'person',
                'question_text': f'What is {person.name.strip()}\'s relationship to you?',
                'options': _options(relation, [m.relationship for m in members] + ['friend', 'neighbor', 'caregiver']),
                'correct_answer': relation,
            })
    object_questions = []
    for obj in objects:
        if obj.name.strip() and obj.last_location.strip():
            object_questions.append({
                'question_type': 'object',
                'question_text': f'Where is your {obj.name.strip()} usually kept?',
                'options': _options(obj.last_location.strip(), [o.last_location for o in objects] +
                                    ['kitchen counter', 'bedroom table', 'living room']),
                'correct_answer': obj.last_location.strip(),
            })
    random.shuffle(person_questions)
    random.shuffle(object_questions)
    # Alternate personalized question categories, then use orientation as a fallback.
    pool = []
    while person_questions or object_questions:
        if person_questions:
            pool.append(person_questions.pop())
        if object_questions:
            pool.append(object_questions.pop())
    pool.extend(_orientation_question(kind) for kind in ('weekday', 'month', 'year'))
    return pool


def _recent_batch(db: Session, user_id: int, quiz_date: str, count: int) -> list:
    latest = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id, QuizAttempt.quiz_date == quiz_date,
    ).order_by(QuizAttempt.id.desc()).limit(count).all()
    return list(reversed(latest))


def build_daily_questions(db: Session, user_id: int, quiz_date: str, count: int = 3) -> list:
    """Return the latest set; answered questions remain as immutable history."""
    existing = _recent_batch(db, user_id, quiz_date, count)
    if existing:
        return existing
    return refresh_daily_questions(db, user_id, quiz_date, count)[0]


def refresh_daily_questions(db: Session, user_id: int, quiz_date: str, count: int = 3) -> tuple[list, int]:
    """Add genuinely new prompts, preserving answered attempts and prior results.

    The active batch is the latest three questions. If no fresh prompt exists, keep
    the old batch rather than silently showing the same quiz as newly refreshed.
    """
    previous = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id, QuizAttempt.quiz_date == quiz_date,
    ).all()
    seen = {(item.question_text.casefold(), item.correct_answer.casefold()) for item in previous}
    candidates = [item for item in _question_pool(db, user_id)
                  if (item['question_text'].casefold(), item['correct_answer'].casefold()) not in seen]
    picked = candidates[:count]
    if not picked:
        return _recent_batch(db, user_id, quiz_date, count), 0
    # Keep earlier attempts, including unanswered ones, so later refreshes never
    # misrepresent a previously offered question as new. The UI shows the latest
    # three while the trends include all question offers and actual answers.
    added = []
    for item in picked:
        row = QuizAttempt(user_id=user_id, quiz_date=quiz_date,
                          question_type=item['question_type'], question_text=item['question_text'],
                          options=json.dumps(item['options']), correct_answer=item['correct_answer'])
        db.add(row)
        added.append(row)
    db.commit()
    # The UI must only show the new batch; older answered attempts stay in trends.
    return _recent_batch(db, user_id, quiz_date, count), len(added)


def serialize_attempt(row: QuizAttempt) -> dict:
    return {
        "id": row.id,
        "quiz_date": row.quiz_date,
        "question_type": row.question_type,
        "question_text": row.question_text,
        "options": json.loads(row.options or "[]"),
        "answered": row.patient_answer is not None,
        "patient_answer": row.patient_answer,
        "is_correct": row.is_correct,
        "created_at": row.created_at.isoformat() + "Z",
    }


def record_answer(db: Session, row: QuizAttempt, answer: str) -> QuizAttempt:
    row.patient_answer = answer.strip()[:160]
    row.is_correct = row.patient_answer.casefold() == row.correct_answer.casefold()
    row.answered_at = utc_now()
    db.commit()
    db.refresh(row)
    return row
