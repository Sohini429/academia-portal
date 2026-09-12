"""Student profile, skill management and skill-gap storage."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Skill, SkillGap, Student, StudentSkill, User
from ..responses import ok
from ..schemas import (
    ScoreUpdate,
    SkillGapIn,
    SkillGapOut,
    StudentOut,
    StudentSkillIn,
    StudentSkillOut,
    StudentUpdate,
)
from ..security import current_user, require_role

router = APIRouter(prefix="/api/students", tags=["students"])


def _get_student(db: Session, user_id: int) -> Student:
    student = db.get(Student, user_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student profile not found")
    return student


def _authorize(viewer: User, student_id: int) -> None:
    """Students see only themselves; colleges and recruiters may view any profile."""
    if viewer.role == "student" and viewer.id != student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You may only access your own profile")


@router.get("/me")
def my_profile(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    return ok(StudentOut.model_validate(_get_student(db, user.id)))


@router.patch("/me")
def update_my_profile(
    payload: StudentUpdate,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    student = _get_student(db, user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return ok(StudentOut.model_validate(student))


@router.get("/{student_id}")
def get_profile(student_id: int, viewer: User = Depends(current_user), db: Session = Depends(get_db)):
    _authorize(viewer, student_id)
    return ok(StudentOut.model_validate(_get_student(db, student_id)))


# --------------------------------------------------------------------------- #
# Skills
# --------------------------------------------------------------------------- #
@router.get("/{student_id}/skills")
def list_skills(student_id: int, viewer: User = Depends(current_user), db: Session = Depends(get_db)):
    _authorize(viewer, student_id)
    student = _get_student(db, student_id)
    return ok([StudentSkillOut.model_validate(s) for s in student.skills])


@router.put("/{student_id}/skills")
def upsert_skills(
    student_id: int,
    payload: list[StudentSkillIn],
    viewer: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Add or update skills. Also the write path used by the AI engine after a
    resume parse (source="resume"). Existing rows keep the higher proficiency.
    """
    _authorize(viewer, student_id)
    _get_student(db, student_id)

    unknown = [s.skill_id for s in payload if db.get(Skill, s.skill_id) is None]
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown skill ids: {', '.join(unknown)}")

    for item in payload:
        row = db.get(StudentSkill, (student_id, item.skill_id))
        if row is None:
            db.add(StudentSkill(student_id=student_id, **item.model_dump()))
        else:
            row.proficiency = max(row.proficiency, item.proficiency)
            row.verified = row.verified or item.verified
            row.source = item.source
    db.commit()
    student = _get_student(db, student_id)
    return ok([StudentSkillOut.model_validate(s) for s in student.skills])


@router.delete("/{student_id}/skills/{skill_id}", status_code=status.HTTP_200_OK)
def delete_skill(
    student_id: int,
    skill_id: str,
    viewer: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _authorize(viewer, student_id)
    row = db.get(StudentSkill, (student_id, skill_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill not present on this profile")
    db.delete(row)
    db.commit()
    return ok({"deleted": skill_id})


# --------------------------------------------------------------------------- #
# Skill gaps & scores (written by the matching engine, read by dashboards)
# --------------------------------------------------------------------------- #
@router.get("/{student_id}/gaps")
def list_gaps(student_id: int, viewer: User = Depends(current_user), db: Session = Depends(get_db)):
    _authorize(viewer, student_id)
    gaps = db.scalars(
        select(SkillGap).where(SkillGap.student_id == student_id).order_by(SkillGap.priority.desc())
    ).all()
    return ok([SkillGapOut.model_validate(g) for g in gaps])


@router.put("/{student_id}/gaps")
def replace_gaps(
    student_id: int,
    payload: list[SkillGapIn],
    viewer: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Full replacement - a gap report is recomputed as a whole, never patched."""
    _authorize(viewer, student_id)
    _get_student(db, student_id)

    unknown = [g.skill_id for g in payload if db.get(Skill, g.skill_id) is None]
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown skill ids: {', '.join(unknown)}")

    for old in db.scalars(select(SkillGap).where(SkillGap.student_id == student_id)):
        db.delete(old)
    db.flush()
    db.add_all([SkillGap(student_id=student_id, **g.model_dump()) for g in payload])
    db.commit()

    gaps = db.scalars(
        select(SkillGap).where(SkillGap.student_id == student_id).order_by(SkillGap.priority.desc())
    ).all()
    return ok([SkillGapOut.model_validate(g) for g in gaps])


@router.patch("/{student_id}/score")
def set_readiness_score(
    student_id: int,
    payload: ScoreUpdate,
    viewer: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _authorize(viewer, student_id)
    student = _get_student(db, student_id)
    if payload.readiness_score is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "readiness_score is required")
    student.readiness_score = payload.readiness_score
    db.commit()
    return ok({"student_id": student_id, "readiness_score": student.readiness_score})
