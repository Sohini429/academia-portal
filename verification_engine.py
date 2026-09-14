"""
Skill Verification Engine
---------------------------
Adds a short, easy quiz (3 questions) for skills that were extracted with
low confidence, or that a student wants to self-verify. This feeds into
the "Assessment Performance" (20% weight) part of the Employability Score.

Design:
- 2 out of 3 correct = skill marked "verified"
- Otherwise = skill stays "self_reported" (still shown, just weighted less)
- No time pressure, no negative marking, no trick questions.
"""

import json
import random


def load_question_bank(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_quiz_for_skill(skill_id: str, bank: dict) -> list:
    """Return the quiz questions for a skill, WITHOUT the correct answers
    (this is what gets sent to the frontend/student)."""
    skill = bank.get(skill_id)
    if not skill:
        return []

    questions = []
    for q in skill["questions"]:
        questions.append({
            "question": q["question"],
            "options": q["options"],
        })
    return questions


def score_quiz(skill_id: str, bank: dict, submitted_answers: list) -> dict:
    """
    submitted_answers: list of option-indexes the student picked, in the
    same order the questions were shown, e.g. [1, 2, 0]

    Returns a result dict with the score and pass/fail status.
    """
    skill = bank.get(skill_id)
    if not skill:
        return {"status": "error", "message": f"Unknown skill_id: {skill_id}"}

    correct_answers = [q["correct_index"] for q in skill["questions"]]

    if len(submitted_answers) != len(correct_answers):
        return {"status": "error", "message": "Answer count does not match question count"}

    score = sum(
        1 for given, correct in zip(submitted_answers, correct_answers)
        if given == correct
    )
    total = len(correct_answers)
    passed = score >= 2  # 2 out of 3 correct = verified

    return {
        "status": "success",
        "skill_id": skill_id,
        "skill_name": skill["skill_name"],
        "score": score,
        "total": total,
        "verified": passed,
    }


def verification_badge(passed: bool) -> str:
    return "Verified" if passed else "Self-reported"


# ---------------------------------------------------------------
# Simple CLI demo — lets you try taking a quiz yourself in the terminal
# ---------------------------------------------------------------
if __name__ == "__main__":
    bank = load_question_bank("questions_bank_sample.json")

    print("Available demo skills:", ", ".join(bank.keys()))
    skill_id = input("Enter a skill_id to take the quiz (e.g. SKL-101): ").strip()

    quiz = get_quiz_for_skill(skill_id, bank)
    if not quiz:
        print("No quiz found for that skill_id.")
        raise SystemExit

    print(f"\nQuiz for {bank[skill_id]['skill_name']} — pick the option number (1-{len(quiz[0]['options'])})\n")

    answers = []
    for i, q in enumerate(quiz, start=1):
        print(f"Q{i}. {q['question']}")
        for j, opt in enumerate(q["options"], start=1):
            print(f"   {j}. {opt}")
        choice = int(input("Your answer: ").strip())
        answers.append(choice - 1)  # convert to 0-indexed
        print()

    result = score_quiz(skill_id, bank, answers)
    print(f"Score: {result['score']}/{result['total']}")
    print(f"Result: {verification_badge(result['verified'])}")
