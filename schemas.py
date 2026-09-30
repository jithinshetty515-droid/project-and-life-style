from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    role: Optional[str] = Field(default=None, max_length=160)
    avg_weekday_study_hours: Optional[float] = Field(default=None, ge=0, le=16)
    timezone: Optional[str] = Field(default=None, max_length=64)


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: str = "Medium"
    target_date: Optional[datetime] = None

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v not in ("Low", "Medium", "High"):
            raise ValueError("priority must be Low, Medium or High")
        return v


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    subject: str = ""
    category: str = "assignment"
    deadline: Optional[datetime] = None
    estimated_hours: float = Field(default=0, ge=0, le=200)
    progress: float = Field(default=0, ge=0, le=100)
    priority: str = "Medium"

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in ("assignment", "exam", "other"):
            raise ValueError("category must be assignment, exam or other")
        return v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v not in ("Low", "Medium", "High"):
            raise ValueError("priority must be Low, Medium or High")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    subject: Optional[str] = None
    category: Optional[str] = None
    deadline: Optional[datetime] = None
    estimated_hours: Optional[float] = Field(default=None, ge=0, le=200)
    progress: Optional[float] = Field(default=None, ge=0, le=100)
    priority: Optional[str] = None
    status: Optional[str] = None


class WhatIfRequest(BaseModel):
    question: str = Field(default="", max_length=600)
    horizon_days: int = Field(default=2, ge=1, le=7)


class FeedbackRequest(BaseModel):
    question: str = ""
    recommendation_shown: str = ""
    useful: bool = True
    reason: Optional[str] = None
    chosen_scenario: Optional[str] = None
    note: str = ""


class PermissionUpdate(BaseModel):
    category: str
    enabled: bool


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)