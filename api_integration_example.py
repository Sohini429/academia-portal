"""
API Integration Example — Skill Verification Engine
------------------------------------------------------
Shows Member 2 how the quiz endpoints would plug into the backend.
Two endpoints:
  GET  /skills/{skill_id}/quiz     -> fetch quiz questions (no answers)
  POST /skills/{skill_id}/submit   -> submit answers, get verified/not
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from verification_engine import load_question_bank, get_quiz_for_skill, score_quiz

app = FastAPI()
bank = load_question_bank("questions_bank_sample.json")


class QuizSubmission(BaseModel):
    student_id: str
    answers: list[int]  # e.g. [1, 2, 0]


@app.get("/skills/{skill_id}/quiz")
def fetch_quiz(skill_id: str):
    quiz = get_quiz_for_skill(skill_id, bank)
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz available for this skill")

    return {
        "status": "success",
        "data": {"skill_id": skill_id, "questions": quiz},
        "timestamp": None,
        "errors": None,
    }


@app.post("/skills/{skill_id}/submit")
def submit_quiz(skill_id: str, submission: QuizSubmission):
    result = score_quiz(skill_id, bank, submission.answers)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    # TODO (Member 2): update student_skills table here —
    # set verified=True/False for (student_id, skill_id) based on result["verified"]
    # this feeds into the Assessment Performance (20%) part of the Employability Score

    return {
        "status": "success",
        "data": result,
        "timestamp": None,
        "errors": None,
    }
