"""Pydantic request/response models. These define the integration contract
the frontend, AI and matching modules code against.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["student", "college", "industry"]
JobType = Literal["full-time", "internship", "contract"]
AppStatus = Literal["applied", "shortlisted", "rejected", "hired"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role
    name: str = Field(min_length=2, max_length=200)
    # role-specific extras, all optional
    college_name: str | None = None
    branch: str | None = None
    graduation_year: int | None = Field(default=None, ge=1990, le=2100)
    cgpa: float | None = Field(default=None, ge=0, le=10)
    industry: str | None = None
    city: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserOut(ORMModel):
    id: int
    email: EmailStr
    role: Role
    is_active: bool
    created_at: datetime


# --------------------------------------------------------------------------- #
# Skill registry
# --------------------------------------------------------------------------- #
class SkillOut(ORMModel):
    id: str
    canonical_name: str
    category: str
    parent_skill_id: str | None = None
    description: str | None = None


class SkillCreate(BaseModel):
    id: str = Field(pattern=r"^SKL-\d{3,6}$")
    canonical_name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=60)
    parent_skill_id: str | None = None
    description: str | None = None
    aliases: list[str] = []


class SkillResolveRequest(BaseModel):
    """Used by the AI engine to map raw extracted text onto canonical Skill IDs."""

    terms: list[str] = Field(min_length=1, max_length=500)


# --------------------------------------------------------------------------- #
# Student profile & skills
# --------------------------------------------------------------------------- #
class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    college_id: int | None = None
    college_name: str | None = None
    branch: str | None = None
    graduation_year: int | None = Field(default=None, ge=1990, le=2100)
    cgpa: float | None = Field(default=None, ge=0, le=10)
    phone: str | None = Field(default=None, max_length=20)
    github_url: str | None = Field(default=None, max_length=255)


class StudentSkillIn(BaseModel):
    skill_id: str
    proficiency: int = Field(default=1, ge=1, le=5)
    source: Literal["manual", "resume", "assessment"] = "manual"
    verified: bool = False


class StudentSkillOut(ORMModel):
    skill_id: str
    proficiency: int
    source: str
    verified: bool
    skill: SkillOut


class StudentOut(ORMModel):
    user_id: int
    name: str
    college_id: int | None = None
    college_name: str | None = None
    branch: str | None = None
    graduation_year: int | None = None
    cgpa: float | None = None
    phone: str | None = None
    github_url: str | None = None
    resume_url: str | None = None
    readiness_score: float | None = None
    skills: list[StudentSkillOut] = []


# --------------------------------------------------------------------------- #
# Jobs
# --------------------------------------------------------------------------- #
class JobSkillIn(BaseModel):
    skill_id: str
    required_proficiency: int = Field(default=3, ge=1, le=5)
    is_mandatory: bool = True
    weight: float = Field(default=1.0, gt=0, le=10)


class JobSkillOut(ORMModel):
    skill_id: str
    required_proficiency: int
    is_mandatory: bool
    weight: float
    skill: SkillOut


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=10)
    location: str | None = None
    type: JobType = "full-time"
    min_cgpa: float | None = Field(default=None, ge=0, le=10)
    required_skills: list[JobSkillIn] = []


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = None
    location: str | None = None
    type: JobType | None = None
    min_cgpa: float | None = Field(default=None, ge=0, le=10)
    is_open: bool | None = None
    required_skills: list[JobSkillIn] | None = None


class CompanyBrief(ORMModel):
    user_id: int
    name: str
    industry: str | None = None


class JobOut(ORMModel):
    id: int
    company_id: int
    title: str
    description: str
    location: str | None = None
    type: str
    min_cgpa: float | None = None
    is_open: bool
    created_at: datetime
    company: CompanyBrief | None = None
    required_skills: list[JobSkillOut] = []


# --------------------------------------------------------------------------- #
# Applications & gaps
# --------------------------------------------------------------------------- #
class ApplicationCreate(BaseModel):
    job_id: int
    cover_note: str | None = Field(default=None, max_length=2000)


class ApplicationStatusUpdate(BaseModel):
    status: AppStatus


class ApplicantBrief(ORMModel):
    user_id: int
    name: str
    college_name: str | None = None
    branch: str | None = None
    cgpa: float | None = None
    resume_url: str | None = None


class ApplicationOut(ORMModel):
    id: int
    student_id: int
    job_id: int
    status: str
    match_score: float | None = None
    cover_note: str | None = None
    created_at: datetime
    job: JobOut | None = None
    student: ApplicantBrief | None = None


class SkillGapIn(BaseModel):
    skill_id: str
    job_id: int | None = None
    current_proficiency: int = Field(default=0, ge=0, le=5)
    required_proficiency: int = Field(default=3, ge=1, le=5)
    priority: float = Field(default=1.0, ge=0)


class SkillGapOut(ORMModel):
    id: int
    student_id: int
    skill_id: str
    job_id: int | None = None
    current_proficiency: int
    required_proficiency: int
    priority: float
    skill: SkillOut


class ScoreUpdate(BaseModel):
    """Matching engine writes computed numbers back through these endpoints."""

    readiness_score: float | None = Field(default=None, ge=0, le=100)
    match_score: float | None = Field(default=None, ge=0, le=100)
