"""Owner-scoped patient activity insights. The app does not continually monitor users."""
import re
from collections import Counter
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import (
    CaregiverNote,
    DailyTask,
    IdentityReminder,
    ObjectInquiry,
    PersonInquiry,
    QuestionEvent,
    QuizAttempt,
    utc_now,
)


def normalize_object(value: str) -> str:
    return ' '.join(re.findall(r'\w+', value.casefold(), flags=re.UNICODE))[:100]


def object_from_question(question: str, records) -> tuple[str, object | None]:
    """Return a named object only on explicit object-location or naming requests.

    This is text processing, NOT image recognition or visual object detection.
    """
    text = question.casefold().strip()
    if not re.search(r'\b(where|find|locate|lost|misplaced|looking for)\b', text):
        return '', None
    for item in sorted(records, key=lambda r: len(r.name), reverse=True):
        if re.search(rf'(?<!\w){re.escape(item.name.casefold())}(?!\w)', text):
            return item.name, item
    patterns = [
        r'\bwhere (?:is|are|did i (?:put|leave))\s+(?:(?:my|the|a|an)\s+)?([\w][\w\s-]{0,75})',
        r'\b(?:find|locate|lost|misplaced|looking for)\s+(?:(?:my|the|a|an)\s+)?([\w][\w\s-]{0,75})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = re.sub(r'\b(?:please|now|today|again|right now)\b.*$', '', match.group(1)).strip(' ?!.,')
            if candidate and len(candidate.split()) <= 4 and len(candidate) <= 80 and normalize_object(candidate):
                return candidate, None
    return '', None


def add_object_inquiry(db: Session, user_id: int, name: str, record=None, source='question'):
    name = name.strip()[:100]
    db.add(ObjectInquiry(user_id=user_id, object_name=name, normalized_name=normalize_object(name),
                         object_id=record.id if record else None, resolved=bool(record), source=source))


def normalize_person_name(value: str) -> str:
    return ' '.join(re.findall(r"[\w'-]+", value.casefold(), flags=re.UNICODE))[:120]


def person_name_from_question(question: str) -> str:
    """Conservative named-person extraction from explicit questions, not face recognition.

    Avoid guessing a name from references such as 'Who is that person?'.
    """
    text = question.casefold().strip()
    patterns = [
        r"\bwho (?:is|was|are)\s+(?:(?:my|the|a|an)\s+)?([a-z][a-z\s'-]{0,45})",
        r"\bdo you know\s+(?:(?:my|the)\s+)?([a-z][a-z\s'-]{0,45})",
    ]
    stopwords = {'daughter', 'son', 'wife', 'husband', 'partner', 'mother', 'father',
                 'sister', 'brother', 'grandfather', 'grandmother', 'friend', 'neighbor',
                 'doctor', 'caregiver', 'caretaker', 'uncle', 'aunt', 'grandson', 'granddaughter',
                 'that', 'this', 'he', 'she', 'they', 'it', 'someone', 'person', 'man', 'woman'}
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        candidate = re.split(r"\b(?:to me|for me|please|now|today|again|right now|in this photo)\b", match.group(1))[0]
        candidate = candidate.strip(' ?!.,')
        terms = set(candidate.split())
        if candidate and not terms.intersection(stopwords) and len(terms) <= 3 and len(candidate) <= 80:
            return candidate
    return ''


def add_person_inquiry(db: Session, user_id: int, name: str):
    name = name.strip()[:120]
    if not name:
        return
    db.add(PersonInquiry(user_id=user_id, name=name, normalized_name=normalize_person_name(name), resolved=False))


def resolve_matching_object_inquiries(db: Session, user_id: int, name: str, object_id: int):
    normalized = normalize_object(name)
    if not normalized:
        return
    db.query(ObjectInquiry).filter(
        ObjectInquiry.user_id == user_id, ObjectInquiry.normalized_name == normalized, ObjectInquiry.resolved.is_(False),
    ).update({'resolved': True, 'object_id': object_id}, synchronize_session=False)


def resolve_matching_person_inquiries(db: Session, user_id: int, name: str):
    normalized = normalize_person_name(name)
    if not normalized:
        return
    db.query(PersonInquiry).filter(
        PersonInquiry.user_id == user_id, PersonInquiry.normalized_name == normalized, PersonInquiry.resolved.is_(False),
    ).update({'resolved': True}, synchronize_session=False)


def period_filter(query, column, days: int):
    if days:
        return query.filter(column >= utc_now() - timedelta(days=days))
    return query


def get_pending_requests(db: Session, user_id: int, limit: int = 20):
    """Grouped, unread action items from named patient requests."""
    pending_objects = db.query(ObjectInquiry).filter(
        ObjectInquiry.user_id == user_id, ObjectInquiry.resolved.is_(False),
    ).order_by(ObjectInquiry.created_at.desc()).all()
    pending_people = db.query(PersonInquiry).filter(
        PersonInquiry.user_id == user_id, PersonInquiry.resolved.is_(False),
    ).order_by(PersonInquiry.created_at.desc()).all()
    grouped = {}
    for kind, rows in (('object', pending_objects), ('person', pending_people)):
        for row in rows:
            key = (kind, row.normalized_name)
            if key not in grouped:
                grouped[key] = {'id': row.id, 'kind': kind,
                                'name': row.object_name if kind == 'object' else row.name,
                                'at': row.created_at.isoformat() + 'Z', 'count': 0}
            grouped[key]['count'] += 1
    return sorted(grouped.values(), key=lambda item: item['at'], reverse=True)[:limit]


def get_monitoring(db: Session, user_id: int, days: int):
    if days not in (0, 7, 30, 90):
        raise HTTPException(422, 'days must be 0, 7, 30, or 90')
    questions = period_filter(db.query(QuestionEvent).filter(QuestionEvent.user_id == user_id), QuestionEvent.created_at, days).order_by(QuestionEvent.created_at.desc(), QuestionEvent.id.desc()).all()
    objects = period_filter(db.query(ObjectInquiry).filter(ObjectInquiry.user_id == user_id), ObjectInquiry.created_at, days).order_by(ObjectInquiry.created_at.desc(), ObjectInquiry.id.desc()).all()
    identities = period_filter(db.query(IdentityReminder).filter(IdentityReminder.user_id == user_id), IdentityReminder.created_at, days).order_by(IdentityReminder.created_at.desc(), IdentityReminder.id.desc()).all()
    notes = period_filter(db.query(CaregiverNote).filter(CaregiverNote.user_id == user_id), CaregiverNote.created_at, days).order_by(CaregiverNote.created_at.desc(), CaregiverNote.id.desc()).all()
    pending_requests = get_pending_requests(db, user_id)
    counts = Counter(i.normalized_name for i in objects)
    names = {i.normalized_name: i.object_name for i in reversed(objects)}
    top_objects = [{'name': names[k], 'count': n} for k, n in sorted(counts.items(), key=lambda a: (-a[1], a[0]))[:10]]
    missing = [q for q in questions if not q.answered]
    missing_objects = [i for i in objects if not i.resolved]
    followup_counts = Counter(q.normalized for q in missing)
    followup_text = {q.normalized: q.question for q in reversed(missing)}
    followups = [{'kind': 'unanswered_question', 'title': followup_text[key], 'count': count} for key, count in sorted(followup_counts.items(), key=lambda x: (-x[1], x[0]))[:5]]
    object_followups = Counter(i.normalized_name for i in missing_objects)
    followups += [{'kind': 'missing_object', 'title': names[key], 'count': count} for key, count in sorted(object_followups.items(), key=lambda x: (-x[1], x[0]))[:5]]
    timeline = (
        [{'id': f'q-{q.id}', 'kind': 'question', 'title': q.question, 'detail': ('Saved answer found' if q.answered else 'No saved answer'), 'at': q.created_at.isoformat() + 'Z'} for q in questions[:80]]
        + [{'id': f'o-{i.id}', 'kind': 'object', 'title': i.object_name, 'detail': ('Saved location found' if i.resolved else 'Location not saved') + ' · ' + ('Object Finder' if i.source == 'finder' else 'Asked in a question'), 'at': i.created_at.isoformat() + 'Z'} for i in objects[:80]]
        + [{'id': f'p-{p.id}', 'kind': 'person', 'title': p.name,
             'detail': 'Patient saved an enrolled profile reminder · not proof of meeting',
             'at': p.created_at.isoformat() + 'Z'} for p in identities[:80]]
        + [{'id': f'n-{n.id}', 'kind': 'note', 'title': n.text, 'detail': 'Caregiver note', 'at': n.created_at.isoformat() + 'Z'} for n in notes[:80]]
    )
    timeline.sort(key=lambda item: (item['at'], item['id']), reverse=True)
    now = utc_now()
    chart_days = 14 if days == 0 else min(days, 30)
    q_by_day = Counter(q.created_at.date().isoformat() for q in questions)
    o_by_day = Counter(i.created_at.date().isoformat() for i in objects)
    chart = [{'date': (now - timedelta(days=delta)).date().isoformat(),
              'questions': q_by_day.get((now - timedelta(days=delta)).date().isoformat(), 0),
              'objects': o_by_day.get((now - timedelta(days=delta)).date().isoformat(), 0)}
             for delta in range(chart_days - 1, -1, -1)]
    return {
        'period_days': days, 'question_count': len(questions), 'object_request_count': len(objects),
        'unique_objects': len(counts), 'unresolved_object_requests': len(missing_objects),
        'questions_without_saved_answers': len(missing), 'caregiver_note_count': len(notes), 'saved_identity_prompts': len(identities),
        'top_objects': top_objects,
        'recent_objects': [{'id': i.id, 'name': i.object_name, 'resolved': i.resolved,
                            'source': i.source, 'at': i.created_at.isoformat() + 'Z'} for i in objects[:25]],
        'recent_people': [{'id': p.id, 'name': p.name, 'relationship': p.relationship, 'at': p.created_at.isoformat() + 'Z'} for p in identities[:20]],
        'recent_questions': [{'id': q.id, 'question': q.question, 'answered': q.answered,
                              'category': q.category, 'source': q.source, 'at': q.created_at.isoformat() + 'Z'} for q in questions[:25]],
        'needs_attention': sorted(followups, key=lambda item: (-item['count'], item['kind'], item['title']))[:8],
        'daily_activity': chart, 'timeline': timeline[:45],
        'notes': [{'id': n.id, 'text': n.text, 'at': n.created_at.isoformat() + 'Z'} for n in notes[:20]],
        'pending_requests': pending_requests,
        'disclaimer': 'Only recorded in-app interactions. Object requests are NOT camera sightings or object detection. Saved identity prompts do not prove physical encounters. These are not medical measurements.',
    }


def get_task_achievement(db: Session, user_id: int, days: int):
    """Daily task completion/verification summary for the caregiver dashboard."""
    if days not in (0, 7, 30, 90):
        raise HTTPException(422, 'days must be 0, 7, 30, or 90')
    query = db.query(DailyTask).filter(DailyTask.user_id == user_id,
                                        DailyTask.task_date <= date.today().isoformat())
    if days:
        cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
        query = query.filter(DailyTask.task_date >= cutoff)
    tasks = query.order_by(DailyTask.task_date.desc(), DailyTask.id.desc()).all()
    total = len(tasks)
    completed = sum(1 for t in tasks if t.completed_by_patient or t.verification_status == 'verified')
    verified = sum(1 for t in tasks if t.verification_status == 'verified')
    rejected = sum(1 for t in tasks if t.verification_status == 'rejected')
    pending_review = sum(1 for t in tasks if t.completed_by_patient and t.verification_status == 'pending')
    by_day = {}
    for task in tasks:
        slot = by_day.setdefault(task.task_date, {'date': task.task_date, 'total': 0, 'completed': 0, 'verified': 0})
        slot['total'] += 1
        if task.completed_by_patient or task.verification_status == 'verified':
            slot['completed'] += 1
        if task.verification_status == 'verified':
            slot['verified'] += 1
    daily = sorted(by_day.values(), key=lambda row: row['date'])
    return {
        'period_days': days, 'total_tasks': total, 'completed_tasks': completed,
        'verified_tasks': verified, 'rejected_tasks': rejected, 'pending_review': pending_review,
        'completion_rate': round(100 * completed / total, 1) if total else 0,
        'verification_rate': round(100 * verified / total, 1) if total else 0,
        'daily_breakdown': daily,
        'tasks': [{
            'id': t.id, 'title': t.title, 'notes': t.notes, 'task_date': t.task_date,
            'completed_by_patient': t.completed_by_patient,
            'completed_at': t.completed_at.isoformat() + 'Z' if t.completed_at else None,
            'verification_status': t.verification_status,
            'caregiver_comment': t.caregiver_comment,
        } for t in tasks],
        'disclaimer': 'Task completion reflects patient self-report and caregiver verification; it is not a clinical measurement.',
    }


def get_quiz_trends(db: Session, user_id: int, days: int):
    """Daily memory check-in trend summary for the caregiver dashboard."""
    if days not in (0, 7, 30, 90):
        raise HTTPException(422, 'days must be 0, 7, 30, or 90')
    query = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id)
    if days:
        cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
        query = query.filter(QuizAttempt.quiz_date >= cutoff)
    attempts = query.order_by(QuizAttempt.quiz_date.desc(), QuizAttempt.id.desc()).all()
    answered = [a for a in attempts if a.patient_answer is not None]
    correct = sum(1 for a in answered if a.is_correct)
    by_day = {}
    for attempt in attempts:
        slot = by_day.setdefault(attempt.quiz_date, {'date': attempt.quiz_date, 'total': 0, 'answered': 0, 'correct': 0})
        slot['total'] += 1
        if attempt.patient_answer is not None:
            slot['answered'] += 1
            if attempt.is_correct:
                slot['correct'] += 1
    daily = sorted(by_day.values(), key=lambda row: row['date'])
    by_type = Counter(a.question_type for a in answered)
    correct_by_type = Counter(a.question_type for a in answered if a.is_correct)
    inquiries = db.query(QuestionEvent).filter(QuestionEvent.user_id == user_id)
    if days:
        inquiries = period_filter(inquiries, QuestionEvent.created_at, days)
    asked_count = inquiries.count()
    assessment_days = len({a.quiz_date for a in answered})
    # This phase only measures completeness of the in-app observation history;
    # number of questions and recall accuracy cannot determine clinical stage.
    if len(answered) < 3 or asked_count < 3:
        phase, phase_number = 'Starting baseline', 1
    elif len(answered) < 12 or assessment_days < 3 or asked_count < 8:
        phase, phase_number = 'Building a pattern', 2
    else:
        phase, phase_number = 'Ongoing tracking', 3
    return {
        'period_days': days, 'total_questions': len(attempts), 'answered_questions': len(answered),
        'correct_answers': correct,
        'accuracy_rate': round(100 * correct / len(answered), 1) if answered else 0,
        'questions_asked': asked_count, 'assessment_days': assessment_days,
        'tracking_phase': phase, 'tracking_phase_number': phase_number,
        'phase_explanation': ('Data coverage phase based on the number of answered daily check-in '
                              'questions, separate assessment days, and questions asked in the app. '
                              'Higher phase means more observations, NOT better or worse memory.'),
        'daily_breakdown': daily,
        'by_question_type': [{'type': key, 'answered': count, 'correct': correct_by_type.get(key, 0)}
                              for key, count in by_type.items()],
        'disclaimer': 'A simple usage trend built from in-app recall questions. This is not a clinical cognitive assessment or diagnosis.',
    }
