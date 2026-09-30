"""Synthetic demo student: Arjun."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from . import models
from .twin_engine.engine import CATEGORY_META, DEFAULT_PERMISSIONS, refresh_patterns


def _dt(days=0, hour=23, minute=59):
    return (datetime.utcnow() + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)


def load_demo(db: Session):
    for u in db.query(models.User).all():
        db.delete(u)
    db.commit()

    arjun = models.User(name="Arjun", role="Engineering Student")
    db.add(arjun)
    db.flush()

    db.add(
        models.Profile(
            user_id=arjun.id,
            twin_confidence=62.0,
            avg_weekday_study_hours=2.5,
            notes="Prefers evening study. Engineering student.",
        )
    )

    for title, prio in [
        ("Score well in upcoming exams", "High"),
        ("Complete assignments on time", "High"),
        ("Maintain consistent sleep", "Medium"),
        ("Improve programming skills", "Medium"),
    ]:
        db.add(models.Goal(user_id=arjun.id, title=title, priority=prio))

    prefs = [
        ("study_time", "evening", "Prefers studying in the evening"),
        ("session_length", "60-90", "Likes focused 60–90 minute study sessions"),
        ("morning_study", "avoid", "Avoids early-morning study"),
        ("difficult_first", "yes", "Prefers difficult subjects before easier subjects"),
        ("assignment_style", "deadline", "Usually completes assignments close to the deadline"),
        ("planning", "needed", "Stays consistent when sessions are planned"),
        ("break_length", "15", "Prefers 15-minute breaks between sessions"),
    ]
    for k, v, label in prefs:
        db.add(models.Preference(user_id=arjun.id, key=k, value=v, label=label, source="user", active=True))

    for label, s, e, cat in [
        ("College", "09:00", "16:00", "college"),
        ("Study window", "18:00", "21:00", "study"),
        ("Wind down", "21:00", "22:30", "personal"),
        ("Sleep", "22:30", "06:30", "sleep"),
    ]:
        db.add(models.RoutineItem(user_id=arjun.id, label=label, start_time=s, end_time=e, category=cat))

    db.add(
        models.Task(
            user_id=arjun.id,
            title="Physics Assignment",
            subject="Physics",
            category="assignment",
            deadline=_dt(1),
            estimated_hours=4.0,
            progress=0.0,
            priority="High",
        )
    )
    db.add(
        models.Task(
            user_id=arjun.id,
            title="Mathematics Exam",
            subject="Mathematics",
            category="exam",
            deadline=_dt(3),
            estimated_hours=8.0,
            progress=45.0,
            priority="High",
        )
    )
    db.add(
        models.Task(
            user_id=arjun.id,
            title="Programming Assignment",
            subject="Programming",
            category="assignment",
            deadline=_dt(5),
            estimated_hours=5.0,
            progress=0.0,
            priority="Medium",
        )
    )

    for i, (hours, hour) in enumerate([(2.5, 18), (2.0, 19), (3.0, 18), (2.5, 20), (1.5, 18), (2.0, 19)]):
        db.add(
            models.Decision(
                user_id=arjun.id,
                kind="study_session",
                description=f"Evening study session ({hours}h)",
                outcome="completed",
                meta=f'{{"hours": {hours}, "hour": {hour}, "planned": true}}',
                occurred_at=datetime.utcnow() - timedelta(days=i + 1),
            )
        )

    for days_before in [1, 1, 0, 2, 1]:
        db.add(
            models.Decision(
                user_id=arjun.id,
                kind="decision",
                description=f"Started assignment {days_before} day(s) before deadline",
                outcome="late_start",
                meta=f'{{"days_before_deadline": {days_before}}}',
                occurred_at=datetime.utcnow() - timedelta(days=days_before + 3),
            )
        )

    for cat, default in DEFAULT_PERMISSIONS.items():
        meta = CATEGORY_META.get(cat, {"description": "", "used_for": ""})
        db.add(
            models.DataPermission(
                user_id=arjun.id,
                category=cat,
                enabled=default,
                description=meta["description"],
                used_for=meta["used_for"],
            )
        )

    db.commit()
    refresh_patterns(db, arjun)
    return {"status": "ok", "user_id": arjun.id, "name": arjun.name}