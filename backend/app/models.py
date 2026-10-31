from datetime import datetime, timezone


def utc_now():
    """UTC timestamp stored as a SQLite-compatible naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship as orm_relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    family_members = orm_relationship("FamilyMember", back_populates="owner")
    memories = orm_relationship("Memory", back_populates="owner")
    objects = orm_relationship("ObjectRecord", back_populates="owner")
    schedules = orm_relationship("ScheduleEntry", back_populates="owner")
    reminders = orm_relationship("Reminder", back_populates="owner")
    preferences = orm_relationship("UserPreference", back_populates="owner")
    contacts = orm_relationship("EmergencyContact", back_populates="owner")
    audits = orm_relationship("AuditLog", back_populates="owner")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    relationship = Column(String, nullable=False)
    photo_url = Column(String, default="/images/default-person.jpg")
    description = Column(Text, default="")
    approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    owner = orm_relationship("User", back_populates="family_members")
    memories = orm_relationship("Memory", back_populates="person")
    face_templates = orm_relationship("FaceTemplate", back_populates="person", cascade="all, delete-orphan")


class ObjectRecord(Base):
    __tablename__ = "object_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, default="personal")
    last_location = Column(String, nullable=False)
    last_seen_at = Column(DateTime, default=utc_now)
    photo_url = Column(String, default="/images/default-object.jpg")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    owner = orm_relationship("User", back_populates="objects")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("family_members.id"), nullable=True)
    title = Column(String, nullable=False)
    caption = Column(String, default="")
    description = Column(Text, default="")
    photo_url = Column(String, default="/images/default-memory.jpg")
    recorded_on = Column(DateTime, default=utc_now)
    voice_note = Column(String, default="")
    approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    owner = orm_relationship("User", back_populates="memories")
    person = orm_relationship("FamilyMember", back_populates="memories")
    media = orm_relationship("MemoryMedia", back_populates="memory", cascade="all, delete-orphan",
                             order_by="MemoryMedia.id")


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    notes = Column(Text, default="")
    approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    owner = orm_relationship("User", back_populates="schedules")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    reminder_time = Column(DateTime, nullable=False)
    notes = Column(Text, default="")
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    owner = orm_relationship("User", back_populates="reminders")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    response_mode = Column(String, default="text")
    voice_first = Column(Boolean, default=False)
    detail_level = Column(String, default="brief")
    reminder_format = Column(String, default="text")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    owner = orm_relationship("User", back_populates="preferences")


class PreferenceHistory(Base):
    __tablename__ = "preference_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    field_name = Column(String, nullable=False)
    old_value = Column(String, default="")
    new_value = Column(String, default="")
    source = Column(String, default="explicit_feedback")
    created_at = Column(DateTime, default=utc_now)


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    relationship = Column(String, default="caregiver")
    notification_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    owner = orm_relationship("User", back_populates="contacts")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    details = Column(Text, default="")
    source = Column(String, default="system")
    created_at = Column(DateTime, default=utc_now)

    owner = orm_relationship("User", back_populates="audits")


class FaceTemplate(Base):
    """Consent-based face embedding; not a photo, scoped to owner and profile."""
    __tablename__ = "face_templates"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=False, index=True)
    embedding = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    person = orm_relationship("FamilyMember", back_populates="face_templates")


class QuestionEvent(Base):
    """Logged questions for optional caregiver analytics in the same local account.

    This is a demo feature; raw question text can be sensitive. Only the signed-in
    account can access or delete this data. No question content is sent to a cloud AI.
    """
    __tablename__ = "question_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    normalized = Column(String(350), nullable=False, index=True)
    category = Column(String(40), default="general", nullable=False)
    answered = Column(Boolean, default=False, nullable=False)
    source = Column(String(12), default="typed", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)


class ObjectInquiry(Base):
    """One intentional patient inquiry about an object. Never claims the item was camera-detected."""
    __tablename__ = "object_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    object_name = Column(String(100), nullable=False)
    normalized_name = Column(String(100), nullable=False, index=True)
    object_id = Column(Integer, nullable=True)  # historical reference, intentionally no FK
    resolved = Column(Boolean, nullable=False, default=False)
    source = Column(String(20), nullable=False, default="question")
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)


class CaregiverNote(Base):
    """Optional caregiver-entered reminder; not a clinical observation."""
    __tablename__ = "caregiver_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)


class IdentityReminder(Base):
    """Opt-in record that a profile prompt was saved, never proof of a real encounter."""
    __tablename__ = "identity_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    family_member_id = Column(Integer, nullable=False)
    name = Column(String(120), nullable=False)
    relationship = Column(String(80), nullable=False)
    source = Column(String(24), default="patient_confirmed", nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)


class PersonInquiry(Base):
    """One intentional patient inquiry naming a person not found in approved profiles.

    Mirrors ObjectInquiry so caregivers get a matching notification when the patient
    asks about a name that is not yet saved, so they can add the profile.
    """
    __tablename__ = "person_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    normalized_name = Column(String(120), nullable=False, index=True)
    resolved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)


class DailyTask(Base):
    """A caregiver-assigned daily task. Patient marks it done; caregiver verifies it."""
    __tablename__ = "daily_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    notes = Column(Text, default="")
    task_date = Column(String(10), nullable=False, index=True)  # ISO date, e.g. 2026-10-30
    completed_by_patient = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime, nullable=True)
    verification_status = Column(String(16), nullable=False, default="pending")  # pending|verified|rejected
    verified_at = Column(DateTime, nullable=True)
    caregiver_comment = Column(Text, default="")
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class QuizAttempt(Base):
    """One personalized daily memory-check question built only from the patient's own saved
    records (family profiles, object locations, today's date). Not a clinical or diagnostic test.
    """
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_date = Column(String(10), nullable=False, index=True)  # ISO date
    question_type = Column(String(32), nullable=False)  # person | object | orientation
    question_text = Column(Text, nullable=False)
    options = Column(Text, nullable=False, default="[]")  # JSON list of strings
    correct_answer = Column(String(160), nullable=False)
    patient_answer = Column(String(160), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class MemoryMedia(Base):
    """Uploaded photos/videos scoped to one memory and one local account."""
    __tablename__ = 'memory_media'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    memory_id = Column(Integer, ForeignKey('memories.id', ondelete='CASCADE'), nullable=False, index=True)
    stored_name = Column(String(80), nullable=False, unique=True)
    original_name = Column(String(255), nullable=False)
    content_type = Column(String(40), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    memory = orm_relationship('Memory', back_populates='media')
