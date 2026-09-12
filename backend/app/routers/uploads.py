"""Resume (PDF) upload storage and controlled retrieval.

Files are stored outside the web root under a server-generated name; the
client never controls the path. The AI engine reads the absolute path from
`GET /api/uploads/resume/{student_id}/path`.
"""
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Student, User
from ..responses import ok
from ..security import current_user, require_role

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
settings = get_settings()

PDF_MAGIC = b"%PDF-"


def _get_student(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student profile not found")
    return student


def _authorize(viewer: User, student_id: int) -> None:
    if viewer.role == "student" and viewer.id != student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You may only access your own resume")


@router.post("/resume", status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    if Path(file.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .pdf resumes are accepted")

    header = file.file.read(len(PDF_MAGIC))
    if header != PDF_MAGIC:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is not a valid PDF")
    file.file.seek(0)

    student = _get_student(db, user.id)
    target = settings.resume_dir / f"{user.id}_{uuid.uuid4().hex}.pdf"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out, length=1024 * 1024)

    if target.stat().st_size > settings.max_resume_bytes:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Resume exceeds {settings.max_resume_bytes // (1024 * 1024)} MB",
        )

    if student.resume_path:  # keep exactly one resume per student
        Path(student.resume_path).unlink(missing_ok=True)

    student.resume_path = str(target)
    student.resume_url = f"/api/uploads/resume/{user.id}"
    db.commit()
    return ok(
        {
            "student_id": user.id,
            "resume_url": student.resume_url,
            "filename": target.name,
            "size_bytes": target.stat().st_size,
        }
    )


@router.get("/resume/{student_id}")
def download_resume(student_id: int, viewer: User = Depends(current_user), db: Session = Depends(get_db)):
    _authorize(viewer, student_id)
    student = _get_student(db, student_id)
    if not student.resume_path or not Path(student.resume_path).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No resume uploaded")
    return FileResponse(student.resume_path, media_type="application/pdf", filename=f"resume_{student_id}.pdf")


@router.get("/resume/{student_id}/path")
def resume_path(student_id: int, viewer: User = Depends(current_user), db: Session = Depends(get_db)):
    """Absolute path for the in-process AI parsing pipeline."""
    _authorize(viewer, student_id)
    student = _get_student(db, student_id)
    if not student.resume_path or not Path(student.resume_path).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No resume uploaded")
    return ok({"student_id": student_id, "path": student.resume_path})


@router.delete("/resume")
def delete_resume(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    student = _get_student(db, user.id)
    if student.resume_path:
        Path(student.resume_path).unlink(missing_ok=True)
    student.resume_path = student.resume_url = None
    db.commit()
    return ok({"student_id": user.id, "deleted": True})
