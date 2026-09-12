"""Relational schema for the Academia-Industry Collaboration Portal.

Mirrors the mapping in the project manual (§5). The `skills` table is the
Master Skill Registry: every other table references a canonical Skill ID
(e.g. "SKL-101") and never a raw text string.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

ROLES = ("student", "college", "industry")
PROFICIENCY_RANGE = "proficiency BETWEEN 1 AND 5"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #
class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('student', 'college', 'industry')", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    student: Mapped["Student | None"] = relationship(back_populates="user", uselist=False)
    college: Mapped["College | None"] = relationship(back_populates="user", uselist=False)
    company: Mapped["Company | None"] = relationship(back_populates="user", uselist=False)


class College(Base):
    __tablename__ = "colleges"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(120))
    university: Mapped[str | None] = mapped_column(String(200))

    user: Mapped[User] = relationship(back_populates="college")
    students: Mapped[list["Student"]] = relationship(back_populates="college")


class Company(Base):
    __tablename__ = "companies"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str | None] = mapped_column(String(120))
    website: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="company")
    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Student(Base):
    __tablename__ = "students"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    college_id: Mapped[int | None] = mapped_column(ForeignKey("colleges.user_id", ondelete="SET NULL"), index=True)
    college_name: Mapped[str | None] = mapped_column(String(200))
    branch: Mapped[str | None] = mapped_column(String(120))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    cgpa: Mapped[float | None] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(20))
    github_url: Mapped[str | None] = mapped_column(String(255))
    # Public download path; the AI engine reads `resume_path` from disk.
    resume_url: Mapped[str | None] = mapped_column(String(255))
    resume_path: Mapped[str | None] = mapped_column(String(500))
    readiness_score: Mapped[float | None] = mapped_column(Float)

    user: Mapped[User] = relationship(back_populates="student")
    college: Mapped[College | None] = relationship(back_populates="students")
    skills: Mapped[list["StudentSkill"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


# --------------------------------------------------------------------------- #
# Master Skill Registry - the single source of truth
# --------------------------------------------------------------------------- #
class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # e.g. SKL-101
    canonical_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    parent_skill_id: Mapped[str | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text)

    aliases: Mapped[list["SkillAlias"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    children: Mapped[list["Skill"]] = relationship()


class SkillAlias(Base):
    """Alternate spellings ("Py", "Python3") used by the AI engine's fast lookup."""

    __tablename__ = "skill_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    skill: Mapped[Skill] = relationship(back_populates="aliases")


class StudentSkill(Base):
    __tablename__ = "student_skills"
    __table_args__ = (CheckConstraint(PROFICIENCY_RANGE, name="ck_student_skills_proficiency"),)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.user_id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    proficiency: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual | resume | assessment
    verified: Mapped[bool] = mapped_column(default=False)

    student: Mapped[Student] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()


# --------------------------------------------------------------------------- #
# Jobs & placement
# --------------------------------------------------------------------------- #
class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (CheckConstraint("type IN ('full-time', 'internship', 'contract')", name="ck_jobs_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # companies.user_id is itself users.id, so this satisfies the manual's
    # "company_id -> users.id" mapping while giving SQLAlchemy a real join.
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.user_id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(20), default="full-time")
    min_cgpa: Mapped[float | None] = mapped_column(Float)
    is_open: Mapped[bool] = mapped_column(default=True)

    company: Mapped[Company] = relationship(back_populates="jobs")
    required_skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (
        CheckConstraint("required_proficiency BETWEEN 1 AND 5", name="ck_job_skills_proficiency"),
    )

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    required_proficiency: Mapped[int] = mapped_column(Integer, default=3)
    is_mandatory: Mapped[bool] = mapped_column(default=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    job: Mapped[Job] = relationship(back_populates="required_skills")
    skill: Mapped[Skill] = relationship()


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("student_id", "job_id", name="uq_application_student_job"),
        CheckConstraint(
            "status IN ('applied', 'shortlisted', 'rejected', 'hired')", name="ck_applications_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.user_id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="applied", index=True)
    match_score: Mapped[float | None] = mapped_column(Float)  # written by the matching engine
    cover_note: Mapped[str | None] = mapped_column(Text)

    student: Mapped[Student] = relationship(back_populates="applications")
    job: Mapped[Job] = relationship(back_populates="applications")


class SkillGap(Base):
    """Per-student missing skill rows produced by the matching engine (Member 5)."""

    __tablename__ = "skill_gaps"
    __table_args__ = (UniqueConstraint("student_id", "skill_id", "job_id", name="uq_skill_gap"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.user_id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    current_proficiency: Mapped[int] = mapped_column(Integer, default=0)
    required_proficiency: Mapped[int] = mapped_column(Integer, default=3)
    priority: Mapped[float] = mapped_column(Float, default=1.0)

    skill: Mapped[Skill] = relationship()
