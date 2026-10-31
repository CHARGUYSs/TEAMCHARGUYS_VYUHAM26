from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "user"


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str


class FamilyMemberCreate(BaseModel):
    name: str
    relationship: str
    description: str = ""
    photo_url: str = "/images/default-person.jpg"
    approved: bool = True


class FamilyMemberOut(FamilyMemberCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class ObjectCreate(BaseModel):
    name: str
    category: str = "personal"
    last_location: str
    last_seen_at: Optional[datetime] = None
    photo_url: str = "/images/default-object.jpg"
    notes: str = ""


class ObjectOut(ObjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class MemoryCreate(BaseModel):
    person_id: Optional[int] = None
    title: str
    caption: str = ""
    description: str = ""
    photo_url: str = "/images/default-memory.jpg"
    recorded_on: Optional[datetime] = None
    voice_note: str = ""
    approved: bool = True


class MemoryMediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    memory_id: int
    original_name: str
    content_type: str
    size_bytes: int
    created_at: datetime


class MemoryOut(MemoryCreate):
    model_config = ConfigDict(from_attributes=True)
    media: list[MemoryMediaOut] = Field(default_factory=list)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class ScheduleCreate(BaseModel):
    title: str
    scheduled_for: datetime
    notes: str = ""
    approved: bool = True


class ScheduleOut(ScheduleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class ReminderCreate(BaseModel):
    title: str
    reminder_time: datetime
    notes: str = ""
    acknowledged: bool = False


class ReminderOut(ReminderCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class PreferenceCreate(BaseModel):
    response_mode: str = Field(default="text")
    voice_first: bool = False
    detail_level: str = Field(default="brief")
    reminder_format: str = Field(default="text")


class PreferenceOut(PreferenceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class EmergencyContactCreate(BaseModel):
    name: str
    phone: str
    relationship: str = "caregiver"
    notification_enabled: bool = True


class EmergencyContactOut(EmergencyContactCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    action: str
    details: str
    source: str
    created_at: datetime


class QuestionRequest(BaseModel):
    question: str
    user_id: Optional[int] = None
    source: str = "typed"


class DailyTaskCreate(BaseModel):
    title: str
    notes: str = ""
    task_date: Optional[str] = None  # ISO date; defaults to today


class DailyTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    notes: str
    task_date: str
    completed_by_patient: bool
    completed_at: Optional[datetime] = None
    verification_status: str
    verified_at: Optional[datetime] = None
    caregiver_comment: str
    created_at: datetime
    updated_at: datetime


class TaskVerifyRequest(BaseModel):
    status: str = Field(pattern="^(verified|rejected|pending)$")
    comment: str = ""


class QuizAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=160)
