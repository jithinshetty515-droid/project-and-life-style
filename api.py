from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models, schemas
from database import get_db
from demo_data import load_demo
import engine
router = APIRouter(prefix="/api")


def _default_user(db: Session):
    u = db.query(models.User).first()
    if not u:
        u = models.User(name="User", role="")
        db.add(u)
        db.commit()
        db.refresh(u)
        for cat, default in engine.DEFAULT_PERMISSIONS.items():
            meta = engine.CATEGORY_META.get(cat, {"description": "", "used_for": ""})
            db.add(
                models.DataPermission(
                    user_id=u.id,
                    category=cat,
                    enabled=default,
                    description=meta["description"],
                    used_for=meta["used_for"],
                )
            )
        db.add(models.Profile(user_id=u.id))
        db.commit()
    return u


@router.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# -------- Profile --------
@router.get("/profile")
def get_profile(db: Session = Depends(get_db)):
    u = _default_user(db)
    return {
        "id": u.id,
        "name": u.name,
        "role": u.role,
        "twin_confidence": u.profile.twin_confidence if u.profile else 0,
        "avg_weekday_study_hours": u.profile.avg_weekday_study_hours if u.profile else 0,
    }


@router.put("/profile")
def update_profile(payload: schemas.ProfileUpdate, db: Session = Depends(get_db)):
    u = _default_user(db)
    if payload.name is not None:
        u.name = payload.name
    if payload.role is not None:
        u.role = payload.role
    if u.profile:
        if payload.avg_weekday_study_hours is not None:
            u.profile.avg_weekday_study_hours = payload.avg_weekday_study_hours
        if payload.timezone is not None:
            u.profile.timezone = payload.timezone
    db.commit()
    return {"status": "updated"}


# -------- Goals --------
@router.get("/goals")
def list_goals(db: Session = Depends(get_db)):
    u = _default_user(db)
    return [
        {"id": g.id, "title": g.title, "priority": g.priority, "status": g.status, "description": g.description}
        for g in u.goals
    ]


@router.post("/goals", status_code=201)
def create_goal(payload: schemas.GoalCreate, db: Session = Depends(get_db)):
    u = _default_user(db)
    g = models.Goal(
        user_id=u.id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        target_date=payload.target_date,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return {"id": g.id, "title": g.title, "priority": g.priority, "status": g.status}


# -------- Tasks --------
@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    u = _default_user(db)
    return [
        {
            "id": t.id,
            "title": t.title,
            "subject": t.subject,
            "category": t.category,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "estimated_hours": t.estimated_hours,
            "progress": t.progress,
            "priority": t.priority,
            "status": t.status,
            "remaining_hours": t.remaining_hours,
        }
        for t in u.tasks
    ]


@router.post("/tasks", status_code=201)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    u = _default_user(db)
    t = models.Task(user_id=u.id, **payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "title": t.title}


@router.put("/tasks/{task_id}")
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    t = db.get(models.Task, task_id)
    if not t:
        raise HTTPException(404, "Task not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    return {"status": "updated"}


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    t = db.get(models.Task, task_id)
    if not t:
        raise HTTPException(404, "Task not found")
    db.delete(t)
    db.commit()
    return None


# -------- Twin --------
@router.get("/twin")
def get_twin(db: Session = Depends(get_db)):
    u = _default_user(db)
    ctx = engine.build_user_context(db, u)

    updates = sorted(u.twin_updates, key=lambda x: x.created_at, reverse=True)[:6]
    return {
        "profile": {
            "name": u.name,
            "role": u.role,
            "twin_confidence": round(u.profile.twin_confidence if u.profile else 0, 1),
            "avg_weekday_study_hours": u.profile.avg_weekday_study_hours if u.profile else 0,
        },
        "goals": [{"id": g.id, "title": g.title, "priority": g.priority} for g in u.goals if g.status == "active"],
        "preferences": [
            {"id": p.id, "key": p.key, "label": p.label, "value": p.value, "source": p.source}
            for p in u.preferences
            if p.active
        ],
        "routine": [
            {"id": r.id, "label": r.label, "start_time": r.start_time, "end_time": r.end_time, "category": r.category}
            for r in u.routine
        ],
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "category": t.category,
                "progress": t.progress,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "estimated_hours": t.estimated_hours,
                "priority": t.priority,
            }
            for t in u.tasks
            if t.status == "open"
        ],
        "patterns": [
            {
                "id": p.id,
                "key": p.key,
                "title": p.title,
                "description": p.description,
                "evidence": p.evidence,
                "confidence": p.confidence,
                "source": p.source,
            }
            for p in u.patterns
        ],
        "recent_updates": [
            {"id": x.id, "title": x.title, "before_text": x.before_text, "after_text": x.after_text, "trigger": x.trigger}
            for x in updates
        ],
        "counts": {
            "goals": len([g for g in u.goals if g.status == "active"]),
            "preferences": len([p for p in u.preferences if p.active]),
            "tasks": len([t for t in u.tasks if t.status == "open"]),
            "patterns": len(u.patterns),
            "decisions": len(u.decisions),
        },
        "context": {
            "preferences": [p.label for p in u.preferences if p.active],
            "routine": [
                {"label": r.label, "start_time": r.start_time, "end_time": r.end_time, "category": r.category}
                for r in u.routine
            ],
            "goals": [g.title for g in u.goals if g.status == "active"],
            "patterns": [p.title for p in u.patterns],
            "missing": ctx.get("missing_categories", []),
        },
    }


@router.get("/twin/context")
def get_context(db: Session = Depends(get_db)):
    u = _default_user(db)
    return engine.build_user_context(db, u)


@router.get("/patterns")
def get_patterns(db: Session = Depends(get_db)):
    u = _default_user(db)
    return [
        {"id": p.id, "key": p.key, "title": p.title, "description": p.description, "evidence": p.evidence, "confidence": p.confidence}
        for p in u.patterns
    ]


@router.post("/twin/reset")
def reset_twin(db: Session = Depends(get_db)):
    for u in db.query(models.User).all():
        db.delete(u)
    db.commit()
    _default_user(db)
    return {"status": "reset"}


# -------- What-If --------
@router.post("/what-if")
def what_if(payload: schemas.WhatIfRequest, db: Session = Depends(get_db)):
    u = _default_user(db)
    return engine.simulate_what_if(db, u, payload.question or "What if I change my plan?", payload.horizon_days)


# -------- Feedback --------
@router.post("/feedback")
def feedback(payload: schemas.FeedbackRequest, db: Session = Depends(get_db)):
    u = _default_user(db)
    result = engine.process_feedback(db, u, payload.model_dump())
    engine.refresh_patterns(db, u)
    return result


# -------- Permissions --------
@router.get("/permissions")
def get_permissions(db: Session = Depends(get_db)):
    u = _default_user(db)
    out = []
    for p in u.permissions:
        count = 0
        if p.category == "goals":
            count = len(u.goals)
        elif p.category == "preferences":
            count = len(u.preferences)
        elif p.category == "routine":
            count = len(u.routine)
        elif p.category == "tasks":
            count = len(u.tasks)
        elif p.category == "study_history":
            count = len([d for d in u.decisions if d.kind == "study_session"])
        elif p.category == "decision_history":
            count = len([d for d in u.decisions if d.kind == "decision"])
        out.append(
            {
                "category": p.category,
                "enabled": p.enabled,
                "description": p.description,
                "used_for": p.used_for,
                "record_count": count,
            }
        )
    return out


@router.put("/permissions")
def update_permission(payload: schemas.PermissionUpdate, db: Session = Depends(get_db)):
    u = _default_user(db)
    p = next((x for x in u.permissions if x.category == payload.category), None)
    if not p:
        raise HTTPException(404, "Unknown category")
    p.enabled = payload.enabled
    db.commit()
    return {"status": "updated", "category": p.category, "enabled": p.enabled}


@router.delete("/permissions/{category}/data")
def delete_category_data(category: str, db: Session = Depends(get_db)):
    u = _default_user(db)
    if category == "goals":
        for x in list(u.goals):
            db.delete(x)
    elif category == "preferences":
        for x in list(u.preferences):
            db.delete(x)
    elif category == "routine":
        for x in list(u.routine):
            db.delete(x)
    elif category == "tasks":
        for x in list(u.tasks):
            db.delete(x)
    elif category in ("study_history", "decision_history"):
        kind = "study_session" if category == "study_history" else "decision"
        for d in list(u.decisions):
            if d.kind == kind:
                db.delete(d)
    elif category == "personal_notes":
        if u.profile:
            u.profile.notes = ""
    else:
        raise HTTPException(400, "Unknown category")
    db.commit()
    return {"status": "deleted", "category": category}


# -------- Demo --------
@router.post("/demo/load")
def demo_load(db: Session = Depends(get_db)):
    return load_demo(db)


# -------- Chat --------
@router.post("/chat")
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    u = _default_user(db)
    return engine.answer_question(db, u, payload.message)
