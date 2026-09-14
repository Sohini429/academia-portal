from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

from engine.matcher import calculate_match
from engine.skill_gap import identify_skill_gaps
from engine.recommender import generate_recommendations
from engine.demand import calculate_skill_demand
from engine.employability import calculate_employability

app = FastAPI(title="Academia-Industry Portal - Member 5 Engine")


class MatchRequest(BaseModel):
    student_skills: dict[str, float]
    job_skills: list[dict]


class DemandRequest(BaseModel):
    jobs: list[list[str]]


class EmployabilityRequest(BaseModel):
    technical_skill_score: float
    job_match: float
    assessment_score: float
    project_score: float
    certification_score: float


@app.get("/")
def home():
    return {
        "status": "success",
        "data": {"message": "Member 5 Engine Running"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "errors": None
    }


@app.post("/match")
def match_student(request: MatchRequest):
    match = calculate_match(request.student_skills, request.job_skills)
    gaps = identify_skill_gaps(request.student_skills, request.job_skills)
    recommendations = generate_recommendations(gaps)

    return {
        "status": "success",
        "data": {
            "match": match,
            "skill_gaps": gaps,
            "recommendations": recommendations
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "errors": None
    }


@app.post("/industry/skill-demand")
def industry_skill_demand(request: DemandRequest):
    demand = calculate_skill_demand(request.jobs)

    return {
        "status": "success",
        "data": {"skill_demand": demand},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "errors": None
    }


@app.post("/employability")
def employability(request: EmployabilityRequest):
    score = calculate_employability(
        request.technical_skill_score,
        request.job_match,
        request.assessment_score,
        request.project_score,
        request.certification_score
    )

    return {
        "status": "success",
        "data": {"employability_score": score},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "errors": None
    }
