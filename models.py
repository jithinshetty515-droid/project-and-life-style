import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def _now():
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, default="User")
    role = Column(String(160), default="")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("Preference", back_populates="user", cascade="all, delete-orphan")
    routine = relationship("RoutineItem", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    patterns = relationship("BehaviorPattern", back_populates="user", cascade="all, delete-orphan")
    twin_updates = relationship("TwinUpdate", back_populates="user", cascade="all, delete-orphan")
    permissions = relationship("DataPermission", back_populates="user", cascade="all, delete-orphan")
    simulations = relationship("ScenarioSimulation", back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    twin_confidence = Column(Float, default=0.0)
    avg_weekday_study_hours = Column(Float, default=0.0)
    timezone = Column(String(64), default="UTC")
    notes = Column(Text, default="")
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="profile")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    priority = Column(String(20), default="Medium")
    status = Column(String(20), default="active")
    target_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User", back_populates="goals")


class Preference(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String(80), nullable=False)
    value = Column(Text, default="")
    label = Column(String(200), default="")
    source = Column(String(20), default="user")
    active = Column(Boolean, default=True)
    evidence = Column(Text, default="")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User", back_populates="preferences")


class RoutineItem(Base):
    __tablename__ = "routine_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    label = Column(String(120), nullable=False)
    start_time = Column(String(5), default="00:00")
    end_time = Column(String(5), default="00:00")
    category = Column(String(40), default="other")
    days = Column(String(80), default="weekdays")
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="routine")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    subject = Column(String(120), default="")
    category = Column(String(30), default="assignment")
    deadline = Column(DateTime, nullable=True)
    estimated_hours = Column(Float, default=0.0)
    progress = Column(Float, default=0.0)
    priority = Column(String(20), default="Medium")
    status = Column(String(20), default="open")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User", back_populates="tasks")

    @property
    def remaining_hours(self):
        return round(max(0.0, (self.estimated_hours or 0.0) * (1 - (self.progress or 0.0) / 100.0)), 2)


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String(40), default="decision")
    description = Column(Text, nullable=False)
    outcome = Column(String(80), default="")
    meta = Column(Text, default="{}")
    occurred_at = Column(DateTime, default=_now)
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="decisions")

    def meta_dict(self):
        try:
            return json.loads(self.meta or "{}")
        except Exception:
            return {}


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, default="")
    recommendation_shown = Column(Text, default="")
    useful = Column(Boolean, default=True)
    reason = Column(String(200), default="")
    note = Column(Text, default="")
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="feedback")


class BehaviorPattern(Base):
    __tablename__ = "behavior_patterns"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String(80), default="")
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    evidence = Column(Text, default="")
    confidence = Column(Float, default=0.5)
    source = Column(String(20), default="inferred")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User", back_populates="patterns")


class TwinUpdate(Base):
    __tablename__ = "twin_updates"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), default="Twin updated")
    before_text = Column(Text, default="")
    after_text = Column(Text, default="")
    trigger = Column(String(200), default="")
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="twin_updates")


class DataPermission(Base):
    __tablename__ = "data_permissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(40), nullable=False)
    enabled = Column(Boolean, default=False)
    description = Column(Text, default="")
    used_for = Column(Text, default="")
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="permissions")


class ScenarioSimulation(Base):
    __tablename__ = "scenario_simulations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, default="")
    horizon_days = Column(Integer, default=2)
    result_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="simulations")