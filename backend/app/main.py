import os
import re
import hashlib
import hmac
import secrets
from datetime import date, datetime, timedelta, timezone
from collections import Counter
from csv import writer as csv_writer
from io import StringIO
from pathlib import Path
from uuid import uuid4
from typing import List, Optional
from pydantic import BaseModel, Field
import json

import cv2
import jwt
import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .vision import detect_faces
from .monitoring import (
    add_object_inquiry,
    add_person_inquiry,
    get_monitoring,
    get_pending_requests,
    get_quiz_trends,
    get_task_achievement,
    normalize_object,
    object_from_question,
    person_name_from_question,
    resolve_matching_object_inquiries,
    resolve_matching_person_inquiries,
)
from . import quiz as quiz_module
from .face_identity import model_status, extract_enrollment, recognize
from .models import (
    AuditLog,
    DailyTask,
    EmergencyContact,
    FamilyMember,
    FaceTemplate,
    QuestionEvent,
    ObjectInquiry,
    CaregiverNote,
    IdentityReminder,
    Memory,
    MemoryMedia,
    ObjectRecord,
    PersonInquiry,
    PreferenceHistory,
    QuizAttempt,
    Reminder,
    ScheduleEntry,
    User,
    UserPreference,
    utc_now,
)
from .schemas import (
    AuditLogOut,
    DailyTaskCreate,
    DailyTaskOut,
    EmergencyContactCreate,
    EmergencyContactOut,
    FamilyMemberCreate,
    FamilyMemberOut,
    MemoryCreate,
    MemoryMediaOut,
    MemoryOut,
    ObjectCreate,
    ObjectOut,
    PreferenceCreate,
    PreferenceOut,
    QuestionRequest,
    QuizAnswerRequest,
    ReminderCreate,
    ReminderOut,
    ScheduleCreate,
    ScheduleOut,
    TaskVerifyRequest,
    UserCreate,
    UserLogin,
    UserOut,
)

load_dotenv()
Base.metadata.create_all(bind=engine)

# Files are private by default: only authenticated owners can stream them.
MEDIA_ROOT = Path(__file__).resolve().parents[1] / 'uploads' / 'memory'
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_VIDEO_BYTES = 40 * 1024 * 1024


def identify_memory_media(data: bytes, declared_type: str) -> tuple[str, str]:
    """Match content signatures to supported safe display types (never SVG/HTML)."""
    signatures = {
        'image/jpeg': (data.startswith(b'\xff\xd8\xff'), '.jpg'),
        'image/png': (data.startswith(b'\x89PNG\r\n\x1a\n'), '.png'),
        'image/webp': (data.startswith(b'RIFF') and data[8:12] == b'WEBP', '.webp'),
        'video/mp4': (len(data) >= 12 and data[4:8] == b'ftyp', '.mp4'),
        'video/webm': (data.startswith(b'\x1a\x45\xdf\xa3'), '.webm'),
    }
    if declared_type not in signatures or not signatures[declared_type][0]:
        raise HTTPException(415, 'Upload JPEG, PNG, WebP, MP4 or WebM files only')
    return declared_type, signatures[declared_type][1]


app = FastAPI(title="ReMind AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations)
    return f'pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}'


def verify_password(password: str, hashed: str) -> bool:
    if hashed.startswith('pbkdf2_sha256$'):
        try:
            _, rounds, salt, digest = hashed.split('$')
            actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds))
            return hmac.compare_digest(actual, bytes.fromhex(digest))
        except (ValueError, OverflowError):
            return False
    if hashed.startswith('$2'):
        # Compatibility with databases created by the previous release.
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except (ImportError, ValueError):
            return False
    return False


SECRET_KEY = os.getenv("SECRET_KEY", "remind-ai-local-development-only-secret")
APP_ENV = os.getenv("APP_ENV", "development").lower()
DEMO_MODE = os.getenv("DEMO_MODE", "true" if APP_ENV == "development" else "false").lower() == "true"
if APP_ENV == "production" and SECRET_KEY == "remind-ai-local-development-only-secret":
    raise RuntimeError("Set a strong SECRET_KEY for production.")
ALGORITHM = "HS256"


def create_access_token(user: User) -> str:
    payload = {"sub": str(user.id), "email": user.email, "role": user.role, "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to access your records")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    user = db.query(User).filter(User.id == int(payload.get("sub", 0))).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found for this token")
    return user


def require_user_access(current_user: User, requested_user_id: Optional[int]) -> int:
    if requested_user_id is None or requested_user_id == current_user.id:
        return current_user.id
    raise HTTPException(status_code=403, detail="Not authorized to access that user")


def create_audit(db: Session, user_id: int, action: str, details: str, source: str = "system") -> None:
    db.add(AuditLog(user_id=user_id, action=action, details=details, source=source))
    db.commit()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "ReMind AI"}


@app.post("/api/detect-person")
async def detect_person(frame: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if frame.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image.")

    image_bytes = await frame.read(5 * 1024 * 1024 + 1)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image exceeds the 5 MB limit.")

    def process():
        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid or unsupported image data.")
        height, width = image.shape[:2]
        if width > 4096 or height > 4096:
            raise HTTPException(status_code=413, detail="Image dimensions exceed 4096 pixels.")
        boxes, detector = detect_faces(image)
        return {
            "face_detected": bool(boxes),
            "face_count": len(boxes),
            "faces": [
                {"x": x / width, "y": y / height, "width": w / width, "height": h / height}
                for x, y, w, h in boxes
            ],
            "detector": detector,
            "identifies_person": False,
        }

    # CPU-intensive OpenCV calls must not block FastAPI's event loop.
    return await run_in_threadpool(process)


async def read_camera_image(frame: UploadFile):
    """Bounded image upload and decode, used for recognition and enrollment."""
    if frame.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Choose a JPEG, PNG, or WebP photo.")
    raw = await frame.read(5 * 1024 * 1024 + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="Image is empty.")
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB. Try a smaller photo.")
    image = await run_in_threadpool(cv2.imdecode, np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Unable to read the image.")
    h, w = image.shape[:2]
    if min(h, w) < 80 or max(h, w) > 4096:
        raise HTTPException(status_code=422, detail="Image must be at least 80px and no more than 4096px per side.")
    return image


@app.post("/api/recognition/install")
async def install_recognition_models(request: Request, current_user: User = Depends(get_current_user)):
    """Local-only fixed, SHA-verified official weights installer for the hackathon demo."""
    if not DEMO_MODE or APP_ENV == 'production' or request.client.host not in ('127.0.0.1', '::1', 'localhost', 'testclient'):
        raise HTTPException(status_code=403, detail='AI model installation is available only for a local development demo.')

    from scripts.download_models import MODELS, download

    def install():
        for config in MODELS:
            download(*config)

    try:
        await run_in_threadpool(install)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Model download failed: {str(exc)[:160]}. Try python scripts/download_models.py in backend.') from exc
    return {'message':'Both AI models installed successfully.', **model_status()}


@app.get("/api/recognition/status")
def recognition_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    state = model_status()
    rows = db.query(FaceTemplate.family_member_id).filter(FaceTemplate.user_id == current_user.id).all()
    counts = {}
    for (person_id,) in rows:
        counts[str(person_id)] = counts.get(str(person_id), 0) + 1
    return {**state, 'enrollments': counts, 'enrolled_people': len(counts)}


@app.post("/api/family-members/{member_id}/enroll")
async def enroll_face(member_id: int, frame: UploadFile = File(...), consent: bool = False,
                      db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id, FamilyMember.user_id == current_user.id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Family profile not found")
    if not member.approved or not consent:
        raise HTTPException(status_code=422, detail="Confirm the person's permission before enrolling a face.")
    if db.query(FaceTemplate).filter(FaceTemplate.user_id == current_user.id, FaceTemplate.family_member_id == member_id).count() >= 5:
        raise HTTPException(status_code=409, detail="This profile already has five samples. Remove its enrollment to start again.")
    image = await read_camera_image(frame)
    try:
        vector = await run_in_threadpool(extract_enrollment, image)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.add(FaceTemplate(user_id=current_user.id, family_member_id=member.id, embedding=json.dumps(vector)))
    db.commit()
    create_audit(db, current_user.id, 'face_enrolled', f'Face sample enrolled for profile {member.id}')
    return {'message': f'Face sample saved for {member.name}', 'samples': db.query(FaceTemplate).filter(FaceTemplate.family_member_id == member.id, FaceTemplate.user_id == current_user.id).count()}


@app.delete("/api/family-members/{member_id}/enrollment")
def clear_enrollment(member_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id, FamilyMember.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Family profile not found")
    deleted = db.query(FaceTemplate).filter(FaceTemplate.family_member_id == member.id, FaceTemplate.user_id == current_user.id).delete()
    db.commit()
    create_audit(db, current_user.id, 'face_enrollment_cleared', f'Cleared {deleted} face samples for {member.id}')
    return {'deleted': deleted}


@app.post("/api/recognize-person")
async def recognize_person(frame: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not model_status()['ready']:
        raise HTTPException(status_code=503, detail=model_status()['message'])
    image = await read_camera_image(frame)
    # Only consented and currently approved family members belonging to this user.
    records = db.query(FaceTemplate, FamilyMember).join(FamilyMember, FaceTemplate.family_member_id == FamilyMember.id).filter(
        FaceTemplate.user_id == current_user.id, FamilyMember.user_id == current_user.id, FamilyMember.approved.is_(True)).all()
    templates = [(member.id, member.name, member.relationship, tpl.embedding) for tpl, member in records]
    try:
        faces = await run_in_threadpool(recognize, image, templates)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        'face_detected': bool(faces), 'face_count': len(faces), 'faces': faces,
        'identified': sum(face['status'] == 'matched' for face in faces),
        'model': 'OpenCV YuNet + SFace', 'enrolled_people': len({tpl[0] for tpl in templates}),
    }


@app.get("/api/users", response_model=List[UserOut])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return [current_user]


@app.post("/api/register", response_model=UserOut)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    create_audit(db, user.id, "user_registered", f"Registered {payload.name}")
    return user


@app.post("/api/login")
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user)
    return {
        "message": "Login successful",
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role},
    }


@app.get("/api/home")
def get_home(user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    activities = db.query(ScheduleEntry).filter(ScheduleEntry.user_id == user_id, ScheduleEntry.scheduled_for >= datetime.now()).order_by(ScheduleEntry.scheduled_for.asc()).limit(3).all()
    reminders = db.query(Reminder).filter(Reminder.user_id == user_id, Reminder.acknowledged.is_(False), Reminder.reminder_time >= datetime.now()).order_by(Reminder.reminder_time.asc()).limit(3).all()
    preferences = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    upcoming_items = sorted(
        [{'title': a.title, 'at': a.scheduled_for.isoformat(), 'kind': 'activity'} for a in activities] +
        [{'title': r.title, 'at': r.reminder_time.isoformat(), 'kind': 'reminder'} for r in reminders],
        key=lambda item: (item['at'], item['title']),
    )
    return {
        "user": {"id": user.id, "name": user.name, "role": user.role},
        "next_activity": activities[0].title if activities else "No scheduled activity",
        "next_upcoming": upcoming_items[0] if upcoming_items else None,
        "upcoming_items": upcoming_items,
        "upcoming_reminders": [r.title for r in reminders],
        "preferences": {"response_mode": preferences.response_mode, "voice_first": preferences.voice_first, "detail_level": preferences.detail_level} if preferences else {"response_mode": "text", "voice_first": False},
    }


@app.get("/api/family-members", response_model=List[FamilyMemberOut])
def get_family_members(user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    return db.query(FamilyMember).filter(FamilyMember.user_id == user_id).all()


@app.post("/api/family-members", response_model=FamilyMemberOut)
def add_family_member(payload: FamilyMemberCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    member = FamilyMember(user_id=user_id, **payload.model_dump())
    db.add(member)
    if payload.approved:
        resolve_matching_person_inquiries(db, user_id, payload.name)
    db.commit()
    db.refresh(member)
    create_audit(db, user_id, "family_member_added", f"Added approved profile for {payload.name}")
    return member


@app.put("/api/family-members/{member_id}", response_model=FamilyMemberOut)
def update_family_member(member_id: int, payload: FamilyMemberCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id, FamilyMember.user_id == user_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Family profile not found")
    for field, value in payload.model_dump().items():
        setattr(member, field, value)
    if member.approved:
        resolve_matching_person_inquiries(db, user_id, member.name)
    db.commit()
    db.refresh(member)
    create_audit(db, user_id, "family_member_updated", f"Updated family profile for {member.name}")
    return member


@app.delete("/api/family-members/{member_id}")
def delete_family_member(member_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id, FamilyMember.user_id == user_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Family profile not found")
    member_name = member.name
    for memory in member.memories:
        memory.person_id = None
    db.delete(member)
    db.commit()
    create_audit(db, user_id, "family_member_deleted", f"Deleted family profile for {member_name}")
    return {"message": "Family profile deleted"}


@app.get("/api/objects", response_model=List[ObjectOut])
def get_objects(user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    return db.query(ObjectRecord).filter(ObjectRecord.user_id == user_id).all()


@app.post("/api/objects", response_model=ObjectOut)
def add_object(payload: ObjectCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    _record = ObjectRecord(user_id=user_id, **payload.model_dump())
    if _record.last_seen_at is None:
        _record.last_seen_at = utc_now()
    db.add(_record)
    db.flush()
    resolve_matching_object_inquiries(db, user_id, _record.name, _record.id)
    db.commit()
    db.refresh(_record)
    create_audit(db, user_id, "object_record_added", f"Added object record for {_record.name}")
    return _record


@app.put("/api/objects/{object_id}", response_model=ObjectOut)
def update_object(object_id: int, payload: ObjectCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    record = db.query(ObjectRecord).filter(ObjectRecord.id == object_id, ObjectRecord.user_id == user_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Object record not found")
    for field, value in payload.model_dump().items():
        setattr(record, field, value)
    if record.last_seen_at is None:
        record.last_seen_at = utc_now()
    resolve_matching_object_inquiries(db, user_id, record.name, record.id)
    db.commit()
    db.refresh(record)
    create_audit(db, user_id, "object_record_updated", f"Updated object record for {record.name}")
    return record


@app.delete("/api/objects/{object_id}")
def delete_object(object_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    record = db.query(ObjectRecord).filter(ObjectRecord.id == object_id, ObjectRecord.user_id == user_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Object record not found")
    object_name = record.name
    db.delete(record)
    db.commit()
    create_audit(db, user_id, "object_record_deleted", f"Deleted object record for {object_name}")
    return {"message": "Object record deleted"}


@app.get("/api/memories", response_model=List[MemoryOut])
def get_memories(user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    return db.query(Memory).filter(Memory.user_id == user_id).all()


@app.post("/api/memories", response_model=MemoryOut)
def add_memory(payload: MemoryCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    if payload.person_id is not None and not db.query(FamilyMember).filter(FamilyMember.id == payload.person_id, FamilyMember.user_id == user_id).first():
        raise HTTPException(status_code=422, detail="Linked profile does not belong to this user")
    memory = Memory(user_id=user_id, **payload.model_dump())
    if memory.recorded_on is None:
        memory.recorded_on = utc_now()
    db.add(memory)
    db.commit()
    db.refresh(memory)
    create_audit(db, user_id, "memory_added", f"Added memory {payload.title}")
    return memory


@app.put("/api/memories/{memory_id}", response_model=MemoryOut)
def update_memory(memory_id: int, payload: MemoryCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    memory = db.query(Memory).filter(Memory.id == memory_id, Memory.user_id == user_id).first()
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    if payload.person_id is not None and not db.query(FamilyMember).filter(FamilyMember.id == payload.person_id, FamilyMember.user_id == user_id).first():
        raise HTTPException(status_code=422, detail="Linked profile does not belong to this user")
    for field, value in payload.model_dump().items():
        setattr(memory, field, value)
    if memory.recorded_on is None:
        memory.recorded_on = utc_now()
    db.commit()
    db.refresh(memory)
    create_audit(db, user_id, "memory_updated", f"Updated memory {memory.title}")
    return memory


@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    memory = db.query(Memory).filter(Memory.id == memory_id, Memory.user_id == user_id).first()
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    memory_title = memory.title
    uploaded_paths = [MEDIA_ROOT / item.stored_name for item in memory.media]
    db.delete(memory)
    db.commit()
    for path in uploaded_paths:
        path.unlink(missing_ok=True)
    create_audit(db, user_id, "memory_deleted", f"Deleted memory {memory_title}")
    return {"message": "Memory deleted"}


def owned_memory(db: Session, user_id: int, memory_id: int) -> Memory:
    memory = db.query(Memory).filter(Memory.user_id == user_id, Memory.id == memory_id).first()
    if memory is None:
        raise HTTPException(404, 'Memory not found')
    return memory


@app.post('/api/memories/{memory_id}/media', response_model=MemoryMediaOut, status_code=201)
async def upload_memory_media(memory_id: int, file: UploadFile = File(...),
                              db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    owned_memory(db, current_user.id, memory_id)
    declared = file.content_type or ''
    max_size = MAX_IMAGE_BYTES if declared.startswith('image/') else MAX_VIDEO_BYTES
    if declared not in {'image/jpeg', 'image/png', 'image/webp', 'video/mp4', 'video/webm'}:
        raise HTTPException(415, 'Upload JPEG, PNG, WebP, MP4 or WebM files only')
    data = await file.read(max_size + 1)
    if not data or len(data) > max_size:
        raise HTTPException(413, 'Image max 8 MB; video max 40 MB')
    media_type, extension = identify_memory_media(data, declared)
    name = uuid4().hex + extension
    destination = MEDIA_ROOT / name
    # Only the random server-generated basename is ever used in filesystem paths.
    destination.write_bytes(data)
    row = MemoryMedia(user_id=current_user.id, memory_id=memory_id,
                      stored_name=name, original_name=Path(file.filename or 'media').name[:255],
                      content_type=media_type, size_bytes=len(data))
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return row


@app.get('/api/memories/media/{media_id}')
def get_memory_media(media_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    row = db.query(MemoryMedia).filter(MemoryMedia.user_id == current_user.id,
                                       MemoryMedia.id == media_id).first()
    if row is None:
        raise HTTPException(404, 'Media not found')
    path = MEDIA_ROOT / row.stored_name
    if not path.is_file():
        raise HTTPException(404, 'Uploaded file is missing')
    return FileResponse(path, media_type=row.content_type, headers={
        'X-Content-Type-Options': 'nosniff',
        'Cache-Control': 'private, no-store',
        'Content-Security-Policy': "default-src 'none'; sandbox",
    })


@app.delete('/api/memories/media/{media_id}')
def delete_memory_media(media_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    row = db.query(MemoryMedia).filter(MemoryMedia.user_id == current_user.id,
                                       MemoryMedia.id == media_id).first()
    if row is None:
        raise HTTPException(404, 'Media not found')
    path = MEDIA_ROOT / row.stored_name
    db.delete(row)
    db.commit()
    path.unlink(missing_ok=True)
    return {'message': 'Media deleted'}


@app.get("/api/schedule", response_model=List[ScheduleOut])
def get_schedule(user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    return db.query(ScheduleEntry).filter(ScheduleEntry.user_id == user_id).order_by(ScheduleEntry.scheduled_for.asc()).all()


@app.post("/api/schedule", response_model=ScheduleOut)
def add_schedule(payload: ScheduleCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    entry = ScheduleEntry(user_id=user_id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    create_audit(db, user_id, "schedule_added", f"Added schedule {payload.title}")
    return entry


@app.put("/api/schedule/{schedule_id}", response_model=ScheduleOut)
def update_schedule(schedule_id: int, payload: ScheduleCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    entry = db.query(ScheduleEntry).filter(ScheduleEntry.id == schedule_id, ScheduleEntry.user_id == user_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Schedule entry not found")
    for field, value in payload.model_dump().items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    create_audit(db, user_id, "schedule_updated", f"Updated schedule {entry.title}")
    return entry


@app.delete("/api/schedule/{schedule_id}")
def delete_schedule(schedule_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    entry = db.query(ScheduleEntry).filter(ScheduleEntry.id == schedule_id, ScheduleEntry.user_id == user_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Schedule entry not found")
    schedule_title = entry.title
    db.delete(entry)
    db.commit()
    create_audit(db, user_id, "schedule_deleted", f"Deleted schedule {schedule_title}")
    return {"message": "Schedule entry deleted"}


@app.get("/api/reminders", response_model=List[ReminderOut])
def get_reminders(user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    return db.query(Reminder).filter(Reminder.user_id == user_id).order_by(Reminder.reminder_time.asc()).all()


@app.post("/api/reminders", response_model=ReminderOut)
def add_reminder(payload: ReminderCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    reminder = Reminder(user_id=user_id, **payload.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    create_audit(db, user_id, "reminder_added", f"Added reminder {payload.title}")
    return reminder


@app.put("/api/reminders/{reminder_id}", response_model=ReminderOut)
def update_reminder(reminder_id: int, payload: ReminderCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.user_id == user_id).first()
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    for field, value in payload.model_dump().items():
        setattr(reminder, field, value)
    db.commit()
    db.refresh(reminder)
    create_audit(db, user_id, "reminder_updated", f"Updated reminder {reminder.title}")
    return reminder


@app.delete("/api/reminders/{reminder_id}")
def delete_reminder(reminder_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.user_id == user_id).first()
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    reminder_title = reminder.title
    db.delete(reminder)
    db.commit()
    create_audit(db, user_id, "reminder_deleted", f"Deleted reminder {reminder_title}")
    return {"message": "Reminder deleted"}


@app.get("/api/preferences", response_model=PreferenceOut)
def get_preferences(user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if pref is None:
        pref = UserPreference(user_id=user_id, response_mode="text", voice_first=False, detail_level="brief", reminder_format="text")
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@app.post("/api/preferences", response_model=PreferenceOut)
def update_preferences(payload: PreferenceCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if pref is None:
        pref = UserPreference(user_id=user_id)
        db.add(pref)
    old = {
        "response_mode": pref.response_mode,
        "voice_first": pref.voice_first,
        "detail_level": pref.detail_level,
        "reminder_format": pref.reminder_format,
    }
    pref.response_mode = payload.response_mode
    pref.voice_first = payload.voice_first
    pref.detail_level = payload.detail_level
    pref.reminder_format = payload.reminder_format
    db.add(PreferenceHistory(user_id=user_id, field_name="response_mode", old_value=str(old["response_mode"]), new_value=payload.response_mode, source="explicit_feedback"))
    db.add(PreferenceHistory(user_id=user_id, field_name="voice_first", old_value=str(old["voice_first"]), new_value=str(payload.voice_first), source="explicit_feedback"))
    db.add(PreferenceHistory(user_id=user_id, field_name="detail_level", old_value=old["detail_level"], new_value=payload.detail_level, source="explicit_feedback"))
    db.add(PreferenceHistory(user_id=user_id, field_name="reminder_format", old_value=old["reminder_format"], new_value=payload.reminder_format, source="explicit_feedback"))
    db.commit()
    db.refresh(pref)
    create_audit(db, user_id, "preferences_updated", f"Updated assistance preferences to {payload.response_mode}")
    return pref


@app.get("/api/emergency", response_model=List[EmergencyContactOut])
def get_emergency_contacts(user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    return db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()


@app.post("/api/emergency", response_model=EmergencyContactOut)
def add_emergency_contact(payload: EmergencyContactCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    contact = EmergencyContact(user_id=user_id, **payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    create_audit(db, user_id, "emergency_contact_added", f"Added emergency contact {payload.name}")
    return contact


@app.put("/api/emergency/{contact_id}", response_model=EmergencyContactOut)
def update_emergency_contact(contact_id: int, payload: EmergencyContactCreate, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    contact = db.query(EmergencyContact).filter(EmergencyContact.id == contact_id, EmergencyContact.user_id == user_id).first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Emergency contact not found")
    for field, value in payload.model_dump().items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    create_audit(db, user_id, "emergency_contact_updated", f"Updated emergency contact {contact.name}")
    return contact


@app.delete("/api/emergency/{contact_id}")
def delete_emergency_contact(contact_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    contact = db.query(EmergencyContact).filter(EmergencyContact.id == contact_id, EmergencyContact.user_id == user_id).first()
    if contact is None:
        raise HTTPException(status_code=404, detail="Emergency contact not found")
    contact_name = contact.name
    db.delete(contact)
    db.commit()
    create_audit(db, user_id, "emergency_contact_deleted", f"Deleted emergency contact {contact_name}")
    return {"message": "Emergency contact deleted"}


@app.get("/api/audit", response_model=List[AuditLogOut])
def get_audit(user_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = require_user_access(current_user, user_id)
    return db.query(AuditLog).filter(AuditLog.user_id == user_id).order_by(AuditLog.created_at.desc()).all()


@app.post("/api/question")
def ask_question(payload: QuestionRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not payload.question.strip() or len(payload.question) > 500:
        raise HTTPException(status_code=422, detail="Enter a question between 1 and 500 characters.")
    user_id = require_user_access(current_user, payload.user_id)
    question = payload.question.casefold().strip()
    question_terms = re.findall(r"\w+", question)
    response = {
        "answer": "I couldn't find that information in your saved memories.",
        "evidence": [],
        "confidence": "low",
        "category": "general",
    }

    family_members = db.query(FamilyMember).filter(
        FamilyMember.user_id == user_id,
        FamilyMember.approved.is_(True),
    ).all()
    objects = db.query(ObjectRecord).filter(ObjectRecord.user_id == user_id).all()
    memories = db.query(Memory).filter(Memory.user_id == user_id).all()
    schedule = db.query(ScheduleEntry).filter(ScheduleEntry.user_id == user_id).order_by(ScheduleEntry.scheduled_for.asc()).all()
    reminders = db.query(Reminder).filter(Reminder.user_id == user_id).order_by(Reminder.reminder_time.asc()).all()
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()

    person_relationships = ("daughter", "son", "wife", "husband", "partner", "mother", "father", "sister", "brother")
    requested_relationship = next(
        (term for term in person_relationships if term in question_terms),
        None,
    )
    named_member = next(
        (
            member
            for member in sorted(family_members, key=lambda item: item.id, reverse=True)
            if member.name.strip()
            if re.search(
                rf"(?<!\w){re.escape(member.name.strip().casefold())}(?!\w)",
                question,
            )
        ),
        None,
    )

    if "who" in question_terms or requested_relationship or named_member or person_name_from_question(payload.question):
        member = named_member
        if member is None and requested_relationship:
            member = next(
                (
                    item
                    for item in family_members
                    if requested_relationship in re.findall(
                        r"\w+", item.relationship.casefold()
                    )
                ),
                None,
            )

        if member:
            relationship = member.relationship.strip()
            if relationship.casefold().startswith("my "):
                relationship = relationship[3:]
            response = {
                "answer": f"This is {member.name.strip()}. {member.name.strip()} is listed in your family profile as your {relationship}.",
                "evidence": [member.description] if member.description else [],
                "confidence": "high",
                "category": "person",
            }
        else:
            response = {
                "answer": "I couldn't find that person in your approved family profiles.",
                "evidence": [],
                "confidence": "low",
                "category": "person",
            }

    # Add a caregiver action item when a patient explicitly asks about an unknown
    # *named* person. Relationship-only questions are not reliable names.
    if response['category'] == 'person' and response['confidence'] == 'low':
        missing_name = person_name_from_question(payload.question)
        if missing_name and not any(
            member.name.casefold().strip() == missing_name.casefold().strip()
            for member in family_members
        ):
            add_person_inquiry(db, user_id, missing_name)

    # Track explicit object requests even if no object record is saved (e.g. pen).
    # This is a named request, NOT a camera sighting or a visual identification.
    object_name, obj = object_from_question(question, objects)
    if object_name:
        if obj:
            response = {
                "answer": f"The last saved location for {obj.name} is {obj.last_location}. This is a caregiver-entered record, not a live tracker.",
                "evidence": [obj.notes] if obj.notes else [],
                "confidence": "high", "category": "object",
            }
        else:
            response = {
                "answer": f"I don't have a saved location for {object_name}. A caregiver can add it in Object records.",
                "evidence": [], "confidence": "low", "category": "object",
            }
        add_object_inquiry(db, user_id, object_name, obj)

    if any(term in question_terms for term in ("memory", "wedding", "story", "remember", "photo")):
        keywords = set(question_terms) - {"what", "is", "the", "my", "our", "a", "about", "show", "me", "tell", "please", "memory", "story", "remember", "photo"}
        ranked = sorted(
            memories,
            key=lambda item: sum(term in (item.title + ' ' + item.caption + ' ' + item.description).casefold() for term in keywords),
            reverse=True,
        )
        memory = ranked[0] if ranked and keywords and any(term in (ranked[0].title + ' ' + ranked[0].description + ' ' + ranked[0].caption).casefold() for term in keywords) else None
        if memory and memory.approved:
            response = {
                "answer": f"I found a saved memory: {memory.title}. {memory.caption or memory.description}",
                "evidence": [memory.description or memory.caption] if (memory.description or memory.caption) else [],
                "confidence": "medium",
                "category": "memory",
            }

    if any(text in question for text in ("what should i do", "next activity", "schedule")):
        next_entry = next((item for item in schedule if item.scheduled_for >= datetime.now()), None)
        if next_entry:
            response = {
                "answer": f"Your next saved activity is {next_entry.title}, scheduled for {next_entry.scheduled_for.strftime('%B %d at %I:%M %p')}.",
                "evidence": [next_entry.notes] if next_entry.notes else [],
                "confidence": "high",
                "category": "schedule",
            }
        else:
            response = {"answer": "There are no upcoming activities in your saved schedule.", "evidence": [], "confidence": "high", "category": "schedule"}

    if "reminder" in question or "appointment" in question:
        next_reminder = next((r for r in reminders if not r.acknowledged and r.reminder_time >= datetime.now()), None)
        if next_reminder:
            response = {
                "answer": f"Your next saved reminder is {next_reminder.title}, at {next_reminder.reminder_time.strftime('%B %d at %I:%M %p')}.",
                "evidence": [next_reminder.notes] if next_reminder.notes else [],
                "confidence": "high",
                "category": "reminder",
            }
        else:
            response = {"answer": "There are no upcoming unacknowledged reminders saved.", "evidence": [], "confidence": "high", "category": "reminder"}

    if "help" in question or "emergency" in question or "sos" in question:
        if contacts:
            first_contact = contacts[0]
            response = {
                "answer": f"Your emergency contact is {first_contact.name} at {first_contact.phone}. You can call them or ask a caregiver to help.",
                "evidence": [first_contact.relationship],
                "confidence": "medium",
                "category": "safety",
            }

    normalized = re.sub(r"[^\w\s]", " ", question, flags=re.UNICODE)
    normalized = " ".join(normalized.split())[:350]
    db.add(QuestionEvent(
        user_id=user_id,
        question=payload.question.strip(),
        normalized=normalized,
        category=response['category'],
        answered=response['confidence'] != 'low',
        source=payload.source if payload.source in {'typed', 'voice', 'quick'} else 'typed',
    ))
    db.commit()
    # Question texts are intentionally excluded from audit log details.
    return response




class ObjectLookupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CareNoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=400)


class IdentityReminderRequest(BaseModel):
    family_member_id: int = Field(gt=0)


@app.post('/api/identity-reminder', status_code=201)
def save_identity_reminder(payload: IdentityReminderRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Explicitly save an enrolled profile reminder. Does not claim proof of meeting."""
    member = db.query(FamilyMember).filter(FamilyMember.id == payload.family_member_id,
                                            FamilyMember.user_id == current_user.id,
                                            FamilyMember.approved.is_(True)).first()
    if not member:
        raise HTTPException(404, 'Enrolled family profile not found')
    if not db.query(FaceTemplate).filter(FaceTemplate.family_member_id == member.id,
                                        FaceTemplate.user_id == current_user.id).first():
        raise HTTPException(422, 'Enroll at least one face photo before saving a profile reminder.')
    item = IdentityReminder(user_id=current_user.id, family_member_id=member.id,
                            name=member.name, relationship=member.relationship)
    db.add(item)
    db.commit()
    return {'message': 'Profile reminder saved for caregiver review; this is not proof of a physical visit.'}


@app.delete('/api/caregiver/identity-reminders')
def delete_identity_reminders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    count = db.query(IdentityReminder).filter(IdentityReminder.user_id == current_user.id).delete()
    db.commit()
    return {'deleted': count}


@app.post('/api/object-lookup')
def object_lookup(payload: ObjectLookupRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Explicit patient lookup. No camera or automatic object recognition involved."""
    name = ' '.join(payload.name.split()).strip()
    if not normalize_object(name):
        raise HTTPException(422, 'Enter an object name, such as pen or glasses.')
    records = db.query(ObjectRecord).filter(ObjectRecord.user_id == current_user.id).all()
    record = next((item for item in records if normalize_object(item.name) == normalize_object(name)), None)
    add_object_inquiry(db, current_user.id, record.name if record else name, record, source='finder')
    db.commit()
    return {'object': record.name if record else name, 'found': bool(record),
            'location': record.last_location if record else None,
            'answer': (f'The last saved location for {record.name} is {record.last_location}. This is not live tracking.'
                       if record else f'No location is saved for {name}. Ask a caregiver to add it.'),
            'source': 'saved_object_record' if record else 'not_found'}


@app.get('/api/caregiver/monitoring')
def caregiver_monitoring(days: int = 30, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_monitoring(db, current_user.id, days)


@app.post('/api/caregiver/notes', status_code=201)
def caregiver_add_note(payload: CareNoteRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(422, 'Note cannot be empty.')
    item = CaregiverNote(user_id=current_user.id, text=text)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {'id': item.id, 'text': item.text, 'at': item.created_at.isoformat() + 'Z'}


@app.delete('/api/caregiver/notes/{note_id}')
def caregiver_remove_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(CaregiverNote).filter(CaregiverNote.id == note_id, CaregiverNote.user_id == current_user.id).first()
    if not item:
        raise HTTPException(404, 'Note not found')
    db.delete(item)
    db.commit()
    return {'deleted': 1}


@app.delete('/api/caregiver/object-lookups')
def caregiver_clear_objects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    deleted = db.query(ObjectInquiry).filter(ObjectInquiry.user_id == current_user.id).delete()
    db.commit()
    return {'deleted': deleted, 'message': 'Object request history cleared.'}


@app.get('/api/caregiver/monitoring.csv')
def caregiver_monitoring_csv(days: int = 30, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _analytics_days(days)
    from .monitoring import period_filter
    records = period_filter(db.query(ObjectInquiry).filter(ObjectInquiry.user_id == current_user.id), ObjectInquiry.created_at, days).order_by(ObjectInquiry.created_at.desc()).all()
    output = StringIO()
    csv = csv_writer(output)
    csv.writerow(['date_utc', 'object_requested', 'saved_location_found', 'source'])
    for event in records:
        name = event.object_name
        if name.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
            name = "'" + name
        csv.writerow([event.created_at.isoformat(), name, event.resolved, event.source])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type='text/csv',
                             headers={'Content-Disposition': 'attachment; filename="remind-object-requests.csv"',
                                      'Cache-Control': 'no-store'})


# Caregiver insights summarize account-owned question history; not medical diagnosis.
def _question_events(db: Session, user_id: int, days: int):
    query = db.query(QuestionEvent).filter(QuestionEvent.user_id == user_id)
    if days > 0:
        query = query.filter(QuestionEvent.created_at >= utc_now() - timedelta(days=days))
    return query.order_by(QuestionEvent.created_at.desc(), QuestionEvent.id.desc()).all()


def _analytics_days(days: int):
    if days not in (0, 7, 30, 90):
        raise HTTPException(status_code=422, detail="days must be 0, 7, 30, or 90")
    return days


@app.get('/api/caregiver/analytics')
def caregiver_analytics(days: int = 30, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    days = _analytics_days(days)
    events = _question_events(db, current_user.id, days)
    counts = Counter(e.normalized for e in events)
    labels = {}
    for e in events:  # newest spelling/capitalization displayed for each normalized question
        labels.setdefault(e.normalized, e.question)
    # Sort by frequency, then normalized text to provide stable results.
    top_questions = [{'question': labels[key], 'count': count} for key, count in
                     sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:8]]
    category_counts = Counter(e.category for e in events)
    answered_count = sum(bool(e.answered) for e in events)
    now = utc_now()
    chart_days = min(days if days else 14, 30)
    chart = []
    by_date = Counter(e.created_at.date().isoformat() for e in events)
    for offset in range(chart_days - 1, -1, -1):
        date = (now - timedelta(days=offset)).date().isoformat()
        chart.append({'date': date, 'count': by_date.get(date, 0)})
    return {
        'period_days': days,
        'total_questions': len(events),
        'answered_questions': answered_count,
        'unanswered_questions': len(events) - answered_count,
        'unique_questions': len(counts),
        'most_asked_question': top_questions[0] if top_questions else None,
        'top_questions': top_questions,
        'by_category': [{'category': key, 'count': value} for key, value in
                        sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))],
        'daily_questions': chart,
        'recent_questions': [
            {'id': e.id, 'question': e.question, 'category': e.category,
             'answered': e.answered, 'source': e.source, 'asked_at': e.created_at.isoformat() + 'Z'}
            for e in events[:20]
        ],
        'note': 'Usage patterns only. Not a measure of memory, cognition, health, or wellbeing.',
    }


@app.get('/api/caregiver/questions.csv')
def caregiver_questions_csv(days: int = 30, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    days = _analytics_days(days)
    output = StringIO()
    csv = csv_writer(output)
    csv.writerow(['date_utc', 'question', 'category', 'answered', 'input_method'])
    for event in _question_events(db, current_user.id, days):
        # Spreadsheet formula injection protection for caregiver-exported text.
        safe_question = event.question
        if safe_question.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
            safe_question = "'" + safe_question
        csv.writerow([event.created_at.isoformat(), safe_question, event.category, event.answered, event.source])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type='text/csv',
                             headers={'Content-Disposition': 'attachment; filename="remind-question-history.csv"',
                                      'Cache-Control': 'no-store'})


@app.delete('/api/caregiver/questions')
def delete_question_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    deleted = db.query(QuestionEvent).filter(QuestionEvent.user_id == current_user.id).delete()
    db.commit()
    return {'deleted': deleted, 'message': 'Question history cleared for this account.'}

# ---------------------------------------------------------------------------
# Caregiver workflow: inbox, daily routines and simple daily recall check-ins.
# All records stay scoped to the signed-in local account. This demo uses a
# shared login for patient/caregiver; it is NOT role-separated clinical software.
# ---------------------------------------------------------------------------

@app.get('/api/caregiver/notifications')
def caregiver_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    requests = get_pending_requests(db, current_user.id, limit=50)
    return {'count': len(requests), 'items': requests}


@app.post('/api/caregiver/requests/{kind}/{request_id}/dismiss')
def dismiss_caregiver_request(kind: str, request_id: int, db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    model = {'object': ObjectInquiry, 'person': PersonInquiry}.get(kind)
    if model is None:
        raise HTTPException(422, 'Request kind must be object or person')
    row = db.query(model).filter(model.user_id == current_user.id, model.id == request_id).first()
    if row is None:
        raise HTTPException(404, 'Request not found')
    # Dismiss the same unresolved name as a group; keep historic inquiry rows.
    db.query(model).filter(model.user_id == current_user.id,
                           model.normalized_name == row.normalized_name,
                           model.resolved.is_(False)).update({'resolved': True}, synchronize_session=False)
    db.commit()
    return {'message': 'Request dismissed'}


@app.get('/api/daily-tasks', response_model=List[DailyTaskOut])
def daily_tasks(task_date: Optional[date] = None, upcoming_days: int = 0,
                db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if upcoming_days < 0 or upcoming_days > 31:
        raise HTTPException(422, 'upcoming_days must be between 0 and 31')
    day = task_date or date.today()
    query = db.query(DailyTask).filter(DailyTask.user_id == current_user.id,
                                       DailyTask.task_date >= day.isoformat(),
                                       DailyTask.task_date <= (day + timedelta(days=upcoming_days)).isoformat())
    return query.order_by(DailyTask.task_date.asc(), DailyTask.created_at.asc(), DailyTask.id.asc()).all()


@app.get('/api/caregiver/daily-tasks', response_model=List[DailyTaskOut])
def caregiver_daily_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(DailyTask).filter(DailyTask.user_id == current_user.id).order_by(
        DailyTask.task_date.asc(), DailyTask.created_at.asc(), DailyTask.id.asc(),
    ).all()


@app.post('/api/caregiver/daily-tasks', response_model=DailyTaskOut, status_code=201)
def create_daily_task(payload: DailyTaskCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    title = payload.title.strip()
    if not title or len(title) > 160 or len(payload.notes) > 1000:
        raise HTTPException(422, 'Enter a task title (max 160 characters) and short notes')
    try:
        day = date.fromisoformat(payload.task_date) if payload.task_date else date.today()
    except (ValueError, TypeError):
        raise HTTPException(422, 'task_date must be YYYY-MM-DD')
    row = DailyTask(user_id=current_user.id, title=title, notes=payload.notes.strip(),
                    task_date=day.isoformat())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.post('/api/daily-tasks/{task_id}/complete', response_model=DailyTaskOut)
def patient_complete_task(task_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    row = db.query(DailyTask).filter(DailyTask.user_id == current_user.id,
                                     DailyTask.id == task_id).first()
    if row is None:
        raise HTTPException(404, 'Task not found')
    if row.task_date != date.today().isoformat():
        raise HTTPException(409, 'Only today’s tasks can be marked complete')
    if row.verification_status == 'verified':
        return row
    row.completed_by_patient = True
    row.completed_at = utc_now()
    row.verification_status = 'pending'
    row.verified_at = None
    db.commit()
    db.refresh(row)
    return row


@app.post('/api/caregiver/daily-tasks/{task_id}/verify', response_model=DailyTaskOut)
def caregiver_verify_task(task_id: int, payload: TaskVerifyRequest,
                          db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(DailyTask).filter(DailyTask.user_id == current_user.id,
                                     DailyTask.id == task_id).first()
    if row is None:
        raise HTTPException(404, 'Task not found')
    if row.task_date > date.today().isoformat():
        raise HTTPException(409, 'Future tasks cannot be verified before their scheduled day')
    if len(payload.comment) > 1000:
        raise HTTPException(422, 'Comment must be under 1000 characters')
    row.verification_status = payload.status
    row.caregiver_comment = payload.comment.strip()
    row.verified_at = utc_now() if payload.status in {'verified', 'rejected'} else None
    if payload.status == 'verified' and not row.completed_at:
        # Caregivers may directly confirm an administered task even if the patient
        # did not self-report. Distinguish this from patient-reported completion.
        row.completed_at = utc_now()
    db.commit()
    db.refresh(row)
    return row


@app.delete('/api/caregiver/daily-tasks/{task_id}')
def caregiver_delete_task(task_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    row = db.query(DailyTask).filter(DailyTask.user_id == current_user.id,
                                     DailyTask.id == task_id).first()
    if row is None:
        raise HTTPException(404, 'Task not found')
    db.delete(row)
    db.commit()
    return {'message': 'Task deleted'}


@app.get('/api/caregiver/task-achievement')
def caregiver_task_achievement(days: int = 30, db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    return get_task_achievement(db, current_user.id, days)


@app.get('/api/daily-quiz')
def get_daily_quiz(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = date.today().isoformat()
    attempts = quiz_module.build_daily_questions(db, current_user.id, today)
    return {'date': today, 'questions': [quiz_module.serialize_attempt(row) for row in attempts],
            'disclaimer': 'A friendly recall activity, not a medical test or cognitive diagnosis.'}


@app.post('/api/daily-quiz/refresh')
def refresh_daily_quiz(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = date.today().isoformat()
    attempts, new_count = quiz_module.refresh_daily_questions(db, current_user.id, today)
    return {'date': today, 'questions': [quiz_module.serialize_attempt(row) for row in attempts],
            'new_count': new_count, 'message': (
                f'{new_count} new questions from the latest saved information.' if new_count
                else 'No fresh questions are available yet. Add more people or object details to create new questions.'
            )}


@app.post('/api/daily-quiz/{attempt_id}/answer')
def answer_daily_quiz(attempt_id: int, payload: QuizAnswerRequest,
                      db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(QuizAttempt).filter(QuizAttempt.user_id == current_user.id,
                                       QuizAttempt.id == attempt_id).first()
    if row is None:
        raise HTTPException(404, 'Quiz question not found')
    if row.quiz_date != date.today().isoformat():
        raise HTTPException(409, 'Only today’s quiz can be answered')
    if row.patient_answer is not None:
        raise HTTPException(409, 'This question was already answered')
    if payload.answer not in json.loads(row.options):
        raise HTTPException(422, 'Choose one of the provided answers')
    row = quiz_module.record_answer(db, row, payload.answer)
    return {'question': quiz_module.serialize_attempt(row), 'correct_answer': row.correct_answer}


@app.get('/api/caregiver/quiz-trends')
def caregiver_quiz_trends(days: int = 30, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return get_quiz_trends(db, current_user.id, days)


@app.post("/api/seed")
def seed_demo_data(request: Request, db: Session = Depends(get_db)):
    if not DEMO_MODE or request.client is None or request.client.host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Demo seeding is only available in local demo mode")
    user_exists = db.query(User).filter(User.email == "demo@remindai.app").first()
    if user_exists:
        return {"message": "Demo data already present"}
    user = User(email="demo@remindai.app", password_hash=hash_password("remind123"), name="Maya Patel", role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(FamilyMember(user_id=user.id, name="Anu", relationship="daughter", description="Your daughter and primary family contact.", photo_url="/images/anu.png"))
    db.add(FamilyMember(user_id=user.id, name="Vikram", relationship="son", description="Your son, who often calls on weekends.", photo_url="/images/vikram.png"))
    db.add(ObjectRecord(user_id=user.id, name="glasses", category="daily", last_location="bedroom table", last_seen_at=datetime.now() - timedelta(days=1), photo_url="/images/glasses.png", notes="Last seen near the bed in the morning."))
    db.add(ObjectRecord(user_id=user.id, name="keys", category="daily", last_location="kitchen drawer", last_seen_at=datetime.now() - timedelta(hours=6), photo_url="/images/keys.png", notes="Usually kept by the door."))
    db.add(ObjectRecord(user_id=user.id, name="pen", category="daily", last_location="desk organizer", last_seen_at=datetime.now() - timedelta(hours=2), notes="Blue pen often used for notes."))
    db.flush()
    anu = db.query(FamilyMember).filter(FamilyMember.user_id == user.id, FamilyMember.name == "Anu").first()
    db.add(Memory(user_id=user.id, person_id=anu.id, title="Anu's wedding", caption="A joyful family celebration.", description="A warm evening with family gathered at Anu's wedding reception.", photo_url="/images/wedding.png", recorded_on=datetime(2024, 6, 10), voice_note="voice/wedding.mp3"))
    db.add(ScheduleEntry(user_id=user.id, title="Lunch with family", scheduled_for=(datetime.now() + timedelta(days=1)).replace(hour=12, minute=30, second=0, microsecond=0), notes="Lunch at the dining table with Anu and family."))
    db.add(Reminder(user_id=user.id, title="Breakfast reminder", reminder_time=(datetime.now() + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0), notes="Breakfast and take morning medications."))
    db.add(EmergencyContact(user_id=user.id, name="Caregiver Support", phone="+1-555-0148", relationship="primary caregiver", notification_enabled=True))
    db.add(UserPreference(user_id=user.id, response_mode="text", voice_first=False, detail_level="brief", reminder_format="text"))
    demo_questions = [
        ('Where are my keys?', 'object', True), ('Who is Anu?', 'person', True),
        ('Where are my keys?', 'object', True), ('When is lunch?', 'schedule', False),
        ('Who is Anu?', 'person', True), ('Where are my keys?', 'object', True),
        ('What is my next reminder?', 'reminder', True), ('Who is my son?', 'person', True),
        ('Where are my glasses?', 'object', True), ('Who is Anu?', 'person', True),
        ('What is my next reminder?', 'reminder', True), ('Tell me about our wedding', 'memory', True),
    ]
    for index, (text, category, answered) in enumerate(demo_questions):
        db.add(QuestionEvent(user_id=user.id, question=text, normalized=' '.join(re.sub(r'[^\w\s]', ' ', text.casefold()).split()),
                             category=category, answered=answered, source='quick' if index % 3 == 0 else 'typed',
                             created_at=utc_now() - timedelta(days=index % 7, hours=index)))
    for index, (name, resolved, source) in enumerate([
        ('pen', True, 'finder'), ('keys', True, 'question'), ('pen', True, 'question'),
        ('glasses', True, 'finder'), ('wallet', False, 'finder'), ('pen', True, 'finder')
    ]):
        db.add(ObjectInquiry(user_id=user.id, object_name=name, normalized_name=normalize_object(name),
                             resolved=resolved, source=source, created_at=utc_now() - timedelta(days=index % 5, hours=index)))
    # Synthetic records demonstrate the new caregiver inbox, verified routines,
    # and recall trend cards without requiring real patient data.
    db.add(PersonInquiry(user_id=user.id, name='Meera', normalized_name='meera', resolved=False))
    demo_day = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    db.add(DailyTask(user_id=user.id, title='Morning medicine check',
                     notes='Caregiver confirms only after checking the prescribed schedule.',
                     task_date=demo_day, verification_status='verified', verified_at=utc_now(),
                     caregiver_comment='Demo: caregiver confirmed the morning check.'))
    db.add(DailyTask(user_id=user.id, title='Morning walk', task_date=demo_day,
                     completed_by_patient=True, completed_at=utc_now(), verification_status='pending'))
    db.add(DailyTask(user_id=user.id, title='Organize the desk', task_date=demo_day))
    db.add(DailyTask(user_id=user.id, title='Put away the keys', task_date=yesterday,
                     completed_by_patient=True, completed_at=utc_now(),
                     verification_status='verified', verified_at=utc_now()))
    for n, correct in [(1, True), (2, True), (2, False), (3, True), (3, False)]:
        quiz_day = (date.today() - timedelta(days=n)).isoformat()
        db.add(QuizAttempt(user_id=user.id, quiz_date=quiz_day,
                           question_type='orientation', question_text='What month is it?',
                           options=json.dumps(['May', 'June', 'July']),
                           correct_answer='May', patient_answer='May' if correct else 'June',
                           is_correct=correct, answered_at=utc_now()))
    db.commit()
    create_audit(db, user.id, "demo_seeded", "Seeded sample ReMind AI records for the demo user.")
    return {"message": "Demo user and sample records created"}


@app.get("/api/evaluation")
def evaluation_dashboard():
    return {
        "status": "not_benchmarked",
        "notes": "No verified accuracy or response-time benchmark is included. Use a labeled test set before reporting metrics.",
        "face_detector": "YuNet if optional model file is installed; otherwise OpenCV Haar cascades",
        "face_identification": "available when both models are installed and consented profiles enrolled",
        "object_image_recognition": False,
    }


@app.get("/")
def root():
    return {"message": "ReMind AI backend active"}
