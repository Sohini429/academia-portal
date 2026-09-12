"""Application submission (students) and applicant review (recruiters)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Application, Job, Student, User
from ..responses import ok
from ..schemas import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationStatusUpdate,
    ScoreUpdate,
)
from ..security import current_user, require_role

router = APIRouter(prefix="/api/applications", tags=["applications"])


def _get_application(db: Session, application_id: int) -> Application:
    app_row = db.scalar(
        select(Application)
        .where(Application.id == application_id)
        .options(selectinload(Application.job), selectinload(Application.student))
    )
    if app_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return app_row


@router.post("", status_code=status.HTTP_201_CREATED)
def apply(
    payload: ApplicationCreate,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    job = db.get(Job, payload.job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if not job.is_open:
        raise HTTPException(status.HTTP_409_CONFLICT, "This posting is closed")
    if db.scalar(
        select(Application).where(
            Application.student_id == user.id, Application.job_id == payload.job_id
        )
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already applied to this job")

    student = db.get(Student, user.id)
    if job.min_cgpa is not None and (student.cgpa or 0) < job.min_cgpa:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"This role requires a CGPA of {job.min_cgpa}")

    row = Application(student_id=user.id, job_id=payload.job_id, cover_note=payload.cover_note)
    db.add(row)
    db.commit()
    return ok(ApplicationOut.model_validate(_get_application(db, row.id)))


@router.get("/mine")
def my_applications(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Application)
        .where(Application.student_id == user.id)
        .options(selectinload(Application.job))
        .order_by(Application.created_at.desc())
    ).all()
    return ok([ApplicationOut.model_validate(r) for r in rows])


@router.get("/job/{job_id}")
def applicants_for_job(
    job_id: int,
    user: User = Depends(require_role("industry")),
    db: Session = Depends(get_db),
):
    """Recruiter's candidate list, sorted by match score (highest first)."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job.company_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own postings")

    rows = db.scalars(
        select(Application)
        .where(Application.job_id == job_id)
        .options(selectinload(Application.student))
        .order_by(Application.match_score.desc().nullslast(), Application.created_at.desc())
    ).all()
    return ok([ApplicationOut.model_validate(r) for r in rows])


@router.patch("/{application_id}/status")
def update_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    user: User = Depends(require_role("industry")),
    db: Session = Depends(get_db),
):
    row = _get_application(db, application_id)
    if row.job.company_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only manage your own postings")
    row.status = payload.status
    db.commit()
    return ok(ApplicationOut.model_validate(_get_application(db, application_id)))


@router.patch("/{application_id}/score")
def set_match_score(
    application_id: int,
    payload: ScoreUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Write path for the matching engine (Member 5)."""
    if payload.match_score is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "match_score is required")
    row = _get_application(db, application_id)
    if user.role == "student" and row.student_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your application")
    row.match_score = payload.match_score
    db.commit()
    return ok({"application_id": application_id, "match_score": row.match_score})
