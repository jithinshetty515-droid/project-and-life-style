"""HumanTwin AI — TwinEngine (deterministic, explainable, rule-based)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy.orm import Session

import models

CATEGORY_META = {
    "goals": {
        "description": "Your stated goals and their priority.",
        "used_for": "Aligning recommendations with what you say matters to you.",
    },
    "preferences": {
        "description": "Study habits, preferred times and working style you told the twin.",
        "used_for": "Choosing study blocks and ordering subjects.",
    },
    "routine": {
        "description": "Your recurring daily schedule (college, study window, sleep).",
        "used_for": "Calculating how much study time actually exists per day.",
    },
    "tasks": {
        "description": "Assignments, exams, deadlines, estimated effort and progress.",
        "used_for": "Computing remaining work and deadline pressure.",
    },
    "calendar": {
        "description": "Dated schedule entries derived from your routine and task deadlines.",
        "used_for": "Placing recommended blocks on real days.",
    },
    "study_history": {
        "description": "Recorded study sessions with duration and time of day.",
        "used_for": "Estimating realistic daily capacity and effective study times.",
    },
    "decision_history": {
        "description": "Past decisions, e.g. when you started an assignment.",
        "used_for": "Identifying behavioral patterns such as delaying assignments.",
    },
    "personal_notes": {
        "description": "Free-text notes you optionally write about yourself.",
        "used_for": "Extra context. Disabled by default.",
    },
}

DEFAULT_PERMISSIONS = {
    "goals": True,
    "preferences": True,
    "routine": True,
    "tasks": True,
    "calendar": True,
    "study_history": True,
    "decision_history": True,
    "personal_notes": False,
}

REASON_ASSIGNMENT_DEADLINE = "The assignment deadline is more important to me"
REASON_PREFER_OTHER_FIRST = "I prefer another task first"
REASON_DEADLINE_LESS = "Deadline is less important to me"
REASON_TIME_DIFFERS = "I have more/less time than expected"
REASON_PRIORITIES_CHANGED = "My priorities changed"
REASON_OTHER = "Other"

POLICY_DEADLINE_FIRST = "deadline_first"
POLICY_EXAM_FIRST = "exam_first"

POLICY_LABELS = {
    POLICY_DEADLINE_FIRST: (
        "When an assignment deadline is within 48 hours, prioritize the assignment "
        "even when an exam is approaching."
    ),
    POLICY_EXAM_FIRST: (
        "Prioritize upcoming exams over assignment deadlines, even when an assignment "
        "is due within 48 hours."
    ),
}


def _now() -> datetime:
    return datetime.utcnow()


def _hm_to_min(value: str) -> int:
    try:
        hours, minutes = str(value).split(":")
        return int(hours) * 60 + int(minutes)
    except Exception:
        return 0


def _min_to_hm(total: float) -> str:
    total = int(round(total)) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def _r(v: float, d: int = 1) -> float:
    return round(float(v), d)


def _permitted(db: Session, user: models.User) -> Dict[str, bool]:
    perms = {p.category: bool(p.enabled) for p in user.permissions}
    for k, v in DEFAULT_PERMISSIONS.items():
        perms.setdefault(k, v)
    return perms


# ---------- 1. Context ----------
def build_user_context(db: Session, user: models.User) -> dict:
    perms = _permitted(db, user)
    missing = [k for k, v in perms.items() if not v]

    ctx = {
        "user": {"name": user.name, "role": user.role},
        "permissions": perms,
        "missing_categories": missing,
        "goals": [],
        "preferences": [],
        "routine": [],
        "tasks": [],
        "history": [],
        "patterns": [],
        "notes": None,
    }

    if perms.get("goals"):
        ctx["goals"] = [
            {"id": g.id, "title": g.title, "priority": g.priority, "status": g.status}
            for g in user.goals
            if g.status == "active"
        ]

    if perms.get("preferences"):
        ctx["preferences"] = [
            {
                "key": p.key,
                "label": p.label or p.value,
                "value": p.value,
                "source": p.source,
                "active": p.active,
            }
            for p in user.preferences
            if p.active
        ]

    if perms.get("routine"):
        ctx["routine"] = [
            {
                "label": r.label,
                "start_time": r.start_time,
                "end_time": r.end_time,
                "category": r.category,
                "days": r.days,
            }
            for r in user.routine
        ]

    if perms.get("tasks") or perms.get("calendar"):
        ctx["tasks"] = [
            {
                "id": t.id,
                "title": t.title,
                "subject": t.subject,
                "category": t.category,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "estimated_hours": t.estimated_hours,
                "progress": t.progress,
                "priority": t.priority,
                "remaining_hours": t.remaining_hours,
                "status": t.status,
            }
            for t in user.tasks
            if t.status == "open"
        ]

    if perms.get("study_history") or perms.get("decision_history"):
        ctx["history"] = [
            {
                "kind": d.kind,
                "description": d.description,
                "outcome": d.outcome,
                "meta": d.meta_dict(),
                "occurred_at": d.occurred_at.isoformat(),
            }
            for d in user.decisions
        ]

    if perms.get("decision_history") or perms.get("study_history"):
        ctx["patterns"] = [
            {
                "key": p.key,
                "title": p.title,
                "description": p.description,
                "evidence": p.evidence,
                "confidence": p.confidence,
            }
            for p in user.patterns
        ]

    if perms.get("personal_notes"):
        ctx["notes"] = user.profile.notes if user.profile else None

    ctx["policy"] = _current_policy(user)
    return ctx


def _current_policy(user):
    for p in user.preferences:
        if p.key == "priority_policy" and p.active:
            return p.value
    return POLICY_EXAM_FIRST


# ---------- 2. Patterns ----------
def identify_patterns(db: Session, user: models.User) -> List[dict]:
    perms = _permitted(db, user)
    patterns: List[dict] = []
    sessions = [d for d in user.decisions if d.kind == "study_session"]
    starts = [d for d in user.decisions if d.kind == "decision"]

    evening = [s for s in sessions if (s.meta_dict().get("hour") or 0) >= 17]
    if sessions and len(evening) >= max(2, int(0.6 * len(sessions))):
        patterns.append(
            {
                "key": "evening_focus",
                "title": "Usually studies more effectively in the evening.",
                "description": "Most recorded study sessions start after 5 PM.",
                "evidence": f"{len(evening)} of {len(sessions)} recorded sessions started in the evening.",
                "confidence": min(0.9, 0.5 + 0.1 * len(evening)),
            }
        )

    postponed = [
        d
        for d in starts
        if d.meta_dict().get("days_before_deadline") is not None
        and d.meta_dict()["days_before_deadline"] <= 1
    ]
    if starts and postponed:
        patterns.append(
            {
                "key": "deadline_delay",
                "title": "Often postpones assignments until close to the deadline.",
                "description": "Assignment work typically starts within 48h of the deadline.",
                "evidence": f"{len(postponed)} of {len(starts)} recorded decisions began within 48h of the deadline.",
                "confidence": min(0.9, 0.5 + 0.1 * len(postponed)),
            }
        )

    if perms.get("preferences"):
        prefs = {p.key for p in user.preferences if p.active}
        if "session_length" in prefs:
            patterns.append(
                {
                    "key": "session_length",
                    "title": "Completes planned study sessions more consistently when limited to 60–90 minutes.",
                    "description": "Stated preference, consistent with recorded session lengths.",
                    "evidence": "Preference: session_length=60-90; durations in history fall in this range.",
                    "confidence": 0.75,
                }
            )
        if "difficult_first" in prefs:
            patterns.append(
                {
                    "key": "difficult_first",
                    "title": "Prefers difficult subjects before easier subjects.",
                    "description": "Stated ordering preference used when planning blocks.",
                    "evidence": "Preference: difficult_first.",
                    "confidence": 0.7,
                }
            )

    if sessions:
        by_day = {}
        for s in sessions:
            d = s.occurred_at.date()
            by_day[d] = by_day.get(d, 0) + (s.meta_dict().get("hours") or 0)
        avg = sum(by_day.values()) / max(1, len(by_day))
        if avg:
            patterns.append(
                {
                    "key": "weekday_avg",
                    "title": f"Typically studies about {round(avg,1)} hours on weekdays.",
                    "description": "Derived from recorded study sessions.",
                    "evidence": f"Average over {len(by_day)} recorded days.",
                    "confidence": min(0.85, 0.4 + 0.05 * len(by_day)),
                }
            )

    if not patterns:
        patterns.append(
            {
                "key": "insufficient",
                "title": "Not enough data to claim behavioral patterns yet.",
                "description": "The twin needs recorded sessions or decisions before asserting a pattern.",
                "evidence": "No qualifying records.",
                "confidence": 0.0,
            }
        )
    return patterns


def refresh_patterns(db: Session, user: models.User):
    fresh = identify_patterns(db, user)
    for p in list(user.patterns):
        db.delete(p)
    db.flush()
    for p in fresh:
        db.add(models.BehaviorPattern(user_id=user.id, **p))
    db.commit()


# ---------- 3. Simulation ----------
def _study_window_hours(routine):
    for r in routine:
        if r.category == "study":
            return max(0.0, (_hm_to_min(r["end_time"]) - _hm_to_min(r["start_time"])) / 60.0)
    return 0.0


def _daily_capacity(user, ctx):
    window = _study_window_hours(ctx["routine"])
    historic = (user.profile.avg_weekday_study_hours if user.profile else 0.0) or 0.0
    if window and historic:
        return min(window, historic), f"min(routine window {window}h, historical {historic}h)"
    return window or historic or 3.0, "single source"


def _deadline_pressure(tasks, capacity_used, horizon):
    score = 0
    reasons = []
    for t in tasks:
        if t["remaining_hours"] <= 0:
            continue
        dl = t.get("deadline")
        if not dl:
            score += 10
            reasons.append(f"{t['title']}: no deadline stored")
            continue
        days = (datetime.fromisoformat(dl) - _now()).total_seconds() / 86400
        if days < 0:
            score += 60
            reasons.append(f"{t['title']} is overdue")
        elif days <= horizon:
            score += 40
            reasons.append(f"{t['title']} deadline falls inside the {horizon}-day horizon")
        elif days <= horizon + 2:
            score += 20
            reasons.append(f"{t['title']} deadline is close")
        if t["remaining_hours"] > 3:
            score += 10
            reasons.append(f"{t['title']} still needs ~{t['remaining_hours']}h (est.)")
    if capacity_used >= 0.9:
        score += 15
        reasons.append("Almost all available study time is consumed")
    level = "High" if score >= 60 else "Moderate" if score >= 30 else "Low"
    return {"level": level, "score": min(100, score), "reasons": reasons}


def _apply_progress(t, hours):
    if t["estimated_hours"] <= 0:
        return t["progress"], t["progress"]
    gained = (hours / t["estimated_hours"]) * 100.0
    after = min(100.0, t["progress"] + gained)
    return t["progress"], round(after, 1)


def _status_for(t, after, horizon):
    dl = t.get("deadline")
    if after >= 100:
        return "Completed"
    if not dl:
        return "At risk"
    days = (datetime.fromisoformat(dl) - _now()).total_seconds() / 86400
    remaining = t["estimated_hours"] * (1 - after / 100.0)
    if days <= horizon and remaining > 0:
        return "Critical"
    if days <= horizon + 2 and remaining > 2:
        return "At risk"
    return "On track"


def simulate_scenario(ctx, user, focus_key, horizon_days):
    tasks = [dict(t) for t in ctx["tasks"]]
    if not tasks:
        return {
            "key": "?",
            "title": "No tasks",
            "description": "No open tasks stored.",
            "total_allocated": 0,
            "time_allocation": [],
            "task_outcomes": [],
            "tasks_completed": [],
            "tasks_delayed": [],
            "deadline_pressure": {"level": "Low", "score": 0, "reasons": []},
            "benefits": [],
            "risks": ["No tasks available to simulate."],
            "conflicts": [],
            "capacity_basis": "",
        }

    daily, basis = _daily_capacity(user, ctx)
    total_capacity = round(daily * horizon_days, 2)

    exams = [t for t in tasks if t["category"] == "exam"]
    assignments = [t for t in tasks if t["category"] != "exam"]
    exams.sort(key=lambda t: t["deadline"] or "9999")
    assignments.sort(key=lambda t: t["deadline"] or "9999")

    if focus_key == "exam_first":
        ordered = exams + assignments
        key, title = "A", "Focus on exam preparation first"
        desc = (
            "Dedicate study capacity to the upcoming exam first, then any leftover time to assignments."
        )
    else:
        ordered = assignments + exams
        key, title = "B", "Complete the nearest assignment first"
        desc = (
            "Prioritise the assignment whose deadline lands inside the horizon, then route remaining capacity to exam preparation."
        )

    remaining_capacity = total_capacity
    allocation = []
    outcomes = []

    for t in ordered:
        if remaining_capacity <= 0 or t["remaining_hours"] <= 0:
            before, after = t["progress"], t["progress"]
            hours = 0
        else:
            hours = min(remaining_capacity, t["remaining_hours"])
            remaining_capacity -= hours
            before, after = _apply_progress(t, hours)
        if hours > 0:
            allocation.append(
                {
                    "title": t["title"],
                    "hours": _r(hours),
                    "percent_of_capacity": round((hours / max(0.01, total_capacity)) * 100, 1),
                }
            )
        outcomes.append(
            {
                "id": t["id"],
                "title": t["title"],
                "progress_before": before,
                "progress_after": after,
                "remaining_hours": _r(t["estimated_hours"] * (1 - after / 100.0), 1),
                "status": _status_for(t, after, horizon_days),
            }
        )

    completed = [o for o in outcomes if o["progress_after"] >= 100]
    delayed = [o for o in outcomes if o["progress_after"] < 100]

    pressure = _deadline_pressure(
        [
            {
                "title": o["title"],
                "remaining_hours": o["remaining_hours"],
                "deadline": next((t["deadline"] for t in tasks if t["id"] == o["id"]), None),
            }
            for o in outcomes
        ],
        (total_capacity - remaining_capacity) / max(0.01, total_capacity),
        horizon_days,
    )

    benefits, risks, conflicts = [], [], []
    if focus_key == "exam_first":
        if exams:
            benefits.append(f"Improves readiness for the {exams[0]['title']} (largest single exam risk).")
        risks.append("Assignment progress barely moves, pushing work close to its deadline.")
        conflicts.append("Evening study window is fully used — no slack for missed sessions.")
    else:
        benefits.append("Removes the nearest deadline risk completely.")
        risks.append("Exam preparation stays below target, increasing exam-day risk.")
        conflicts.append("Exam block is reduced to a shorter session per day.")

    return {
        "key": key,
        "title": title,
        "description": desc,
        "total_allocated": _r(total_capacity - remaining_capacity),
        "time_allocation": allocation,
        "task_outcomes": outcomes,
        "tasks_completed": completed,
        "tasks_delayed": delayed,
        "deadline_pressure": pressure,
        "benefits": benefits,
        "risks": risks,
        "conflicts": conflicts,
        "capacity_basis": basis,
    }


def compare_scenarios(a, b):
    return {
        "capacity_used": {"A": a["total_allocated"], "B": b["total_allocated"]},
        "pressure": {"A": a["deadline_pressure"]["level"], "B": b["deadline_pressure"]["level"]},
        "completed": {
            "A": [c["title"] for c in a["tasks_completed"]],
            "B": [c["title"] for c in b["tasks_completed"]],
        },
    }


# ---------- 4. Recommendation ----------
def generate_recommendation(ctx, scenarios, comparison):
    a, b = scenarios[0], scenarios[1]
    policy = ctx.get("policy", POLICY_EXAM_FIRST)

    if policy == POLICY_DEADLINE_FIRST:
        primary = b["key"]
        reason = (
            "Your stored priority policy prioritises assignment deadlines that fall within 48 hours — learned from your earlier feedback."
        )
    else:
        primary = a["key"]
        reason = (
            "Your stored priority policy places upcoming exams above assignment deadlines unless you tell the twin otherwise."
        )

    risk_order = {"Low": 0, "Moderate": 1, "High": 2}
    lower = min(scenarios, key=lambda s: risk_order.get(s["deadline_pressure"]["level"], 1))

    first_outcome = scenarios[0]["task_outcomes"][0] if scenarios[0]["task_outcomes"] else {"title": "task", "progress_after": 0}
    second_outcome = scenarios[1]["task_outcomes"][0] if scenarios[1]["task_outcomes"] else {"title": "task", "progress_after": 0}

    if primary == "A":
        text = (
            f"{reason} Scenario A concentrates on {first_outcome['title']} and gets it to ~{first_outcome['progress_after']}% (est.), "
            f"while Scenario B clears the nearest assignment deadline. Scenario A carries {a['deadline_pressure']['level'].lower()} "
            f"deadline pressure; Scenario B carries {b['deadline_pressure']['level'].lower()}."
        )
    else:
        text = (
            f"{reason} Scenario B clears the nearest assignment deadline first, then routes remaining time to exam preparation "
            f"(~{second_outcome['progress_after']}% est.). Scenario B carries {b['deadline_pressure']['level'].lower()} deadline "
            f"pressure; Scenario A carries {a['deadline_pressure']['level'].lower()}."
        )

    return {
        "primary_scenario": primary,
        "lower_risk_scenario": lower["key"],
        "text": text,
        "source": "rule_engine",
        "policy_used": policy,
    }


# ---------- 5. Explanation ----------
def generate_explanation(ctx, scenarios, recommendation):
    factors: List[str] = []
    for t in ctx["tasks"]:
        if t.get("deadline"):
            days = (datetime.fromisoformat(t["deadline"]) - _now()).days
            factors.append(f"{t['title']} deadline is in {days} day(s)")
        factors.append(f"{t['title']}: ~{t['remaining_hours']}h remaining, {int(t['progress'])}% done")
    for p in ctx["patterns"][:3]:
        factors.append(p["title"])
    for pr in ctx["preferences"][:4]:
        factors.append(pr["label"])
    daily, basis = _daily_capacity_for_factors(ctx)
    factors.append(f"Estimated daily study capacity ≈ {daily}h ({basis})")

    not_used = []
    for cat in ctx.get("missing_categories", []):
        not_used.append(f"{cat.replace('_', ' ').title()} — disabled in Data Control")

    return {
        "factors": factors,
        "not_used": not_used,
        "disclaimer": (
            "This is decision support, not a guarantee. Figures marked (est.) are estimates derived from your stored data."
        ),
    }


def _daily_capacity_for_factors(ctx):
    window = _study_window_hours(ctx["routine"])
    return window or 3.0, "routine study window"


# ---------- 6. Balanced plan ----------
def _balanced_plan(ctx, horizon_days):
    study = next((r for r in ctx["routine"] if r["category"] == "study"), None)
    start = _hm_to_min(study["start_time"]) if study else 18 * 60
    end = _hm_to_min(study["end_time"]) if study else 21 * 60

    exams = sorted([t for t in ctx["tasks"] if t["category"] == "exam"], key=lambda t: t["deadline"] or "9999")
    assignments = sorted([t for t in ctx["tasks"] if t["category"] != "exam"], key=lambda t: t["deadline"] or "9999")
    hard = exams + assignments
    easy = list(reversed(assignments))

    plan = []
    for d in range(horizon_days):
        day_label = "Day 1 (today)" if d == 0 else f"Day {d + 1}"
        blocks = []
        cursor = start
        if hard:
            blocks.append(
                {
                    "start": _min_to_hm(cursor),
                    "end": _min_to_hm(cursor + 90),
                    "label": hard[0]["title"],
                    "type": "study",
                }
            )
            cursor += 90
        blocks.append({"start": _min_to_hm(cursor), "end": _min_to_hm(cursor + 15), "label": "Break", "type": "break"})
        cursor += 15
        second = hard[1] if len(hard) > 1 else (easy[0] if easy else None)
        if second and cursor + 60 <= end:
            blocks.append(
                {
                    "start": _min_to_hm(cursor),
                    "end": _min_to_hm(cursor + 60),
                    "label": second["title"],
                    "type": "study",
                }
            )
            cursor += 60
        if cursor + 15 <= end:
            blocks.append({"start": _min_to_hm(cursor), "end": _min_to_hm(cursor + 15), "label": "Review", "type": "review"})
        plan.append({"day": day_label, "blocks": blocks})
    return plan


# ---------- 7. Top-level What-If ----------
def simulate_what_if(db: Session, user: models.User, question: str, horizon_days: int = 2) -> dict:
    ctx = build_user_context(db, user)

    if not ctx["tasks"]:
        return {
            "question": question,
            "horizon_days": horizon_days,
            "assumptions": {
                "daily_capacity_hours": 0,
                "total_capacity_hours": 0,
                "total_remaining_hours": 0,
                "notes": ["No tasks stored."],
            },
            "missing_information": ["Tasks"],
            "scenarios": [],
            "recommendation": {
                "primary_scenario": "-",
                "lower_risk_scenario": "-",
                "text": "I cannot simulate without any stored tasks. Load the demo student or add a task.",
                "source": "rule_engine",
            },
            "explanation": {"factors": [], "not_used": [], "disclaimer": ""},
            "balanced_plan": [],
        }

    daily, basis = _daily_capacity(user, ctx)
    total_capacity = round(daily * horizon_days, 2)
    total_remaining = round(sum(t["remaining_hours"] for t in ctx["tasks"]), 2)

    a = simulate_scenario(ctx, user, "exam_first", horizon_days)
    b = simulate_scenario(ctx, user, "assignment_first", horizon_days)
    comparison = compare_scenarios(a, b)
    rec = generate_recommendation(ctx, [a, b], comparison)
    exp = generate_explanation(ctx, [a, b], rec)
    plan = _balanced_plan(ctx, horizon_days)

    db.add(
        models.ScenarioSimulation(
            user_id=user.id,
            question=question,
            horizon_days=horizon_days,
            result_json=json.dumps({"a": a["total_allocated"], "b": b["total_allocated"]}),
        )
    )
    db.commit()

    missing = [c.replace("_", " ").title() for c in ctx.get("missing_categories", [])]

    return {
        "question": question,
        "horizon_days": horizon_days,
        "assumptions": {
            "daily_capacity_hours": _r(daily),
            "total_capacity_hours": _r(total_capacity),
            "total_remaining_hours": _r(total_remaining),
            "notes": [
                f"Daily capacity is an estimate: {basis}.",
                f"Total remaining work is an estimate from stored task data ({total_remaining}h).",
                "Study sessions are assumed to run inside your stored evening study window.",
            ],
        },
        "missing_information": missing,
        "scenarios": [a, b],
        "recommendation": rec,
        "explanation": exp,
        "balanced_plan": plan,
    }


# ---------- 8. Feedback loop ----------
def process_feedback(db: Session, user: models.User, payload: dict) -> dict:
    fb = models.Feedback(
        user_id=user.id,
        question=payload.get("question", ""),
        recommendation_shown=payload.get("recommendation_shown", ""),
        useful=bool(payload.get("useful", True)),
        reason=payload.get("reason") or "",
        note=payload.get("note", ""),
    )
    db.add(fb)

    useful = bool(payload.get("useful", True))
    reason = (payload.get("reason") or "").strip()

    before_policy = _current_policy(user)
    new_policy = before_policy

    if not useful:
        if reason == REASON_ASSIGNMENT_DEADLINE:
            new_policy = POLICY_DEADLINE_FIRST
        elif reason in (REASON_PREFER_OTHER_FIRST, REASON_PRIORITIES_CHANGED):
            new_policy = POLICY_DEADLINE_FIRST if before_policy == POLICY_EXAM_FIRST else POLICY_EXAM_FIRST
        elif reason == REASON_DEADLINE_LESS:
            new_policy = POLICY_EXAM_FIRST
        else:
            new_policy = POLICY_DEADLINE_FIRST if before_policy == POLICY_EXAM_FIRST else POLICY_EXAM_FIRST

    existing = next((p for p in user.preferences if p.key == "priority_policy"), None)
    if existing:
        existing.value = new_policy
        existing.label = POLICY_LABELS[new_policy]
        existing.source = "learned" if new_policy != before_policy else existing.source
        existing.active = True
        existing.evidence = f"Learned from feedback on {_now().date().isoformat()}."
    else:
        db.add(
            models.Preference(
                user_id=user.id,
                key="priority_policy",
                value=new_policy,
                label=POLICY_LABELS[new_policy],
                source="learned",
                active=True,
                evidence=f"Learned from feedback on {_now().date().isoformat()}.",
            )
        )

    before_text = POLICY_LABELS[before_policy]
    after_text = POLICY_LABELS[new_policy]

    title = (
        "New learned preference: when an assignment deadline is within 48 hours, prioritize the assignment even when an exam is approaching."
        if new_policy == POLICY_DEADLINE_FIRST
        else "New learned preference: prioritize upcoming exams over assignment deadlines."
    )

    update = models.TwinUpdate(
        user_id=user.id,
        title=title,
        before_text=before_text,
        after_text=after_text,
        trigger=f"Feedback: {reason or 'positive'}",
    )
    db.add(update)

    if user.profile:
        user.profile.twin_confidence = min(95, (user.profile.twin_confidence or 0) + 4)

    db.commit()

    return {
        "update": {"title": title, "before_text": before_text, "after_text": after_text},
        "learned_preference": {
            "key": "priority_policy",
            "value": new_policy,
            "label": POLICY_LABELS[new_policy],
            "source": "learned",
        },
        "twin_confidence": round(user.profile.twin_confidence if user.profile else 0, 1),
        "policy_before": before_policy,
        "policy_after": new_policy,
    }


def update_twin(db: Session, user: models.User):
    refresh_patterns(db, user)
    if user.profile:
        c = 20
        c += min(20, len(user.preferences) * 3)
        c += min(20, len(user.patterns) * 3)
        c += min(20, len([d for d in user.decisions if d.kind == "study_session"]))
        c += min(15, len(user.feedback) * 5)
        user.profile.twin_confidence = min(95, c)
    db.commit()


# ---------- 9. Chat ----------
def answer_question(db: Session, user: models.User, message: str) -> dict:
    msg = (message or "").strip().lower()
    ctx = build_user_context(db, user)

    if not ctx["tasks"] and not ctx["goals"]:
        return {
            "answer": "I don't have any stored data yet. Load the demo student or add a task — I only answer from data you've allowed me to use.",
            "source": "rule_engine",
            "factors": [],
            "missing_information": ["Tasks", "Goals"],
        }

    if "what if" in msg or "what happens if" in msg:
        res = simulate_what_if(db, user, message, 2)
        rec = res["recommendation"]
        return {
            "answer": rec["text"],
            "source": "rule_engine",
            "factors": res["explanation"]["factors"][:6],
            "missing_information": res["missing_information"],
        }

    if "pattern" in msg or "routine" in msg:
        pats = ctx["patterns"][:4]
        if not pats:
            return {
                "answer": "I haven't recorded enough sessions or decisions to claim a pattern yet.",
                "source": "rule_engine",
                "factors": [],
                "missing_information": ["Study History"],
            }
        answer = "Patterns I see in your stored data:\n- " + "\n- ".join(p["title"] for p in pats)
        return {
            "answer": answer,
            "source": "rule_engine",
            "factors": [p["evidence"] for p in pats],
            "missing_information": [],
        }

    if "falling behind" in msg or "behind" in msg:
        risky = [
            t
            for t in ctx["tasks"]
            if t["progress"] < 40 and t["deadline"] and (datetime.fromisoformat(t["deadline"]) - _now()).days <= 4
        ]
        if not risky:
            answer = "Nothing in your stored data looks at risk right now. Keep going."
        else:
            answer = "Based on your stored deadlines and progress, these are the ones to watch:\n- " + "\n- ".join(
                f"{t['title']}: {int(t['progress'])}% done, ~{t['remaining_hours']}h left (est.)" for t in risky
            )
        return {
            "answer": answer,
            "source": "rule_engine",
            "factors": [f"{t['title']} at {int(t['progress'])}%" for t in risky],
            "missing_information": [],
        }

    if "plan tomorrow" in msg or "plan my day" in msg or "schedule" in msg:
        plan = _balanced_plan(ctx, 1)
        blocks = plan[0]["blocks"] if plan else []
        answer = "Suggested plan (estimate, not a schedule I enforce):\n- " + "\n- ".join(
            f"{b['start']}–{b['end']} {b['label']}" for b in blocks
        )
        return {
            "answer": answer,
            "source": "rule_engine",
            "factors": [
                "Routine study window",
                "Session length preference (60–90 min)",
                "Hard subjects first",
            ],
            "missing_information": [],
        }

    exams = sorted([t for t in ctx["tasks"] if t["category"] == "exam"], key=lambda t: t["deadline"] or "9999")
    assignments = sorted([t for t in ctx["tasks"] if t["category"] != "exam"], key=lambda t: t["deadline"] or "9999")
    policy = ctx.get("policy", POLICY_EXAM_FIRST)

    if policy == POLICY_DEADLINE_FIRST and assignments:
        pick, why = assignments[0], "assignment deadline policy (learned from your feedback)"
    elif exams:
        pick, why = exams[0], "exam priority policy"
    elif assignments:
        pick, why = assignments[0], "nearest open task"
    else:
        return {"answer": "No tasks found.", "source": "rule_engine", "factors": [], "missing_information": []}

    answer = (
        f"Tonight, start with {pick['title']}. It has ~{pick['remaining_hours']}h of work left (est.) "
        f"and you're at {int(pick['progress'])}%. This follows your {why}. "
        f"Keep it inside your evening study window and stop after 90 minutes — that matches your session-length preference."
    )
    return {
        "answer": answer,
        "source": "rule_engine",
        "factors": [
            f"{pick['title']}: {int(pick['progress'])}% done, ~{pick['remaining_hours']}h remaining",
            f"Policy in use: {policy}",
            "Evening study preference",
        ],
        "missing_information": [c.replace("_", " ").title() for c in ctx.get("missing_categories", [])],
    }
