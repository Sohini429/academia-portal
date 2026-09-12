"""Job posting management (recruiters) and job discovery (everyone)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Job, JobSkill, Skill, User
from ..responses import ok
from ..schemas import JobCreate, JobOut, JobSkillIn, JobUpdate
from ..security import current_user, require_role

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_LOAD = (selectinload(Job.required_skills).selectinload(JobSkill.skill), selectinload(Job.company))


def _get_job(db: Session, job_id: int) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id).options(*_LOAD))
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


def _set_required_skills(db: Session, job: Job, skills: list[JobSkillIn]) -> None:
    unknown = [s.skill_id for s in skills if db.get(Skill, s.skill_id) is None]
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown skill ids: {', '.join(unknown)}")
    job.required_skills = [JobSkill(**s.model_dump()) for s in skills]


@router.get("")
def list_jobs(
    skill_id: str | None = Query(default=None, description="Filter by required Skill ID"),
    location: str | None = None,
    type: str | None = None,
    open_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Job).options(*_LOAD)
    if open_only:
        stmt = stmt.where(Job.is_open.is_(True))
    if location:
        stmt = stmt.where(Job.location == location)
    if type:
        stmt = stmt.where(Job.type == type)
    if skill_id:
        stmt = stmt.join(JobSkill).where(JobSkill.skill_id == skill_id)
    jobs = db.scalars(stmt.distinct().order_by(Job.created_at.desc()).offset(offset).limit(limit)).all()
    return ok([JobOut.model_validate(j) for j in jobs])


@router.get("/mine")
def my_jobs(user: User = Depends(require_role("industry")), db: Session = Depends(get_db)):
    jobs = db.scalars(
        select(Job).where(Job.company_id == user.id).options(*_LOAD).order_by(Job.created_at.desc())
    ).all()
    return ok([JobOut.model_validate(j) for j in jobs])


@router.get("/{job_id}")
def get_job(job_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    return ok(JobOut.model_validate(_get_job(db, job_id)))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    user: User = Depends(require_role("industry")),
    db: Session = Depends(get_db),
):
    job = Job(company_id=user.id, **payload.model_dump(exclude={"required_skills"}))
    _set_required_skills(db, job, payload.required_skills)
    db.add(job)
    db.commit()
    return ok(JobOut.model_validate(_get_job(db, job.id)))


@router.patch("/{job_id}")
def update_job(
    job_id: int,
    payload: JobUpdate,
    user: User = Depends(require_role("industry")),
    db: Session = Depends(get_db),
):
    job = _get_job(db, job_id)
    if job.company_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only edit your own postings")

    fields = payload.model_dump(exclude_unset=True)
    skills = fields.pop("required_skills", None)
    for field, value in fields.items():
        setattr(job, field, value)
    if skills is not None:
        _set_required_skills(db, job, [JobSkillIn(**s) for s in skills])
    db.commit()
    return ok(JobOut.model_validate(_get_job(db, job_id)))


@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    user: User = Depends(require_role("industry")),
    db: Session = Depends(get_db),
):
    job = _get_job(db, job_id)
    if job.company_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only delete your own postings")
    db.delete(job)
    db.commit()
    return ok({"deleted": job_id})
