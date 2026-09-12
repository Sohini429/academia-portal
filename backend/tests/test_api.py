"""End-to-end smoke test of the backend contract.

Runs against a throwaway SQLite file so it needs no Postgres:

    pytest -q
"""
import os
import tempfile
from pathlib import Path

import pytest

TMP = Path(tempfile.mkdtemp(prefix="portal-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{TMP / 'test.db'}"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256"
os.environ["UPLOAD_DIR"] = str(TMP / "uploads")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from seed_skills import seed  # noqa: E402


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    seed()
    with TestClient(app) as c:
        yield c


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def envelope(response) -> dict:
    body = response.json()
    assert set(body) == {"status", "data", "timestamp", "errors"}
    return body


def test_full_journey(client):
    # --- registry is seeded and searchable ---------------------------------
    body = envelope(client.get("/api/skills", params={"q": "py"}))
    assert body["status"] == "success"
    assert any(s["id"] == "SKL-101" for s in body["data"])

    # alias lookup resolves raw AI-extracted text to canonical Skill IDs
    resolved = envelope(
        client.post("/api/skills/resolve", json={"terms": ["Py", "postgres", "quantum juggling"]})
    )["data"]
    assert resolved["matched"] == {"Py": "SKL-101", "postgres": "SKL-402"}
    assert resolved["unmatched"] == ["quantum juggling"]

    # --- registration & login ---------------------------------------------
    student = envelope(
        client.post(
            "/api/auth/register",
            json={
                "email": "asha@college.edu",
                "password": "SuperSecret1",
                "role": "student",
                "name": "Asha Rao",
                "cgpa": 8.4,
            },
        )
    )["data"]
    s_token = student["access_token"]

    recruiter = envelope(
        client.post(
            "/api/auth/register",
            json={
                "email": "hr@acme.com",
                "password": "SuperSecret1",
                "role": "industry",
                "name": "Acme Corp",
                "industry": "Software",
            },
        )
    )["data"]
    r_token = recruiter["access_token"]

    assert client.post(
        "/api/auth/register",
        json={"email": "asha@college.edu", "password": "SuperSecret1", "role": "student", "name": "Dup"},
    ).status_code == 409
    assert client.post("/api/auth/login", json={"email": "asha@college.edu", "password": "wrong"}).status_code == 401

    # refresh returns a fresh, usable access token
    refreshed = envelope(client.post("/api/auth/refresh", json={"refresh_token": student["refresh_token"]}))["data"]
    assert client.get("/api/auth/me", headers=auth(refreshed["access_token"])).status_code == 200
    # a refresh token must not be accepted as an access token
    assert client.get("/api/auth/me", headers=auth(student["refresh_token"])).status_code == 401
    assert client.get("/api/auth/me").status_code == 401

    # --- student profile & skills -----------------------------------------
    profile = envelope(
        client.patch("/api/students/me", json={"branch": "CSE", "github_url": "https://github.com/asha"}, headers=auth(s_token))
    )["data"]
    assert profile["branch"] == "CSE"

    skills = envelope(
        client.put(
            f"/api/students/{student['user']['id']}/skills",
            json=[
                {"skill_id": "SKL-101", "proficiency": 4, "source": "resume"},
                {"skill_id": "SKL-401", "proficiency": 3},
            ],
            headers=auth(s_token),
        )
    )["data"]
    assert {s["skill_id"] for s in skills} == {"SKL-101", "SKL-401"}

    # unknown Skill IDs are rejected - the registry is the only source of truth
    assert client.put(
        f"/api/students/{student['user']['id']}/skills",
        json=[{"skill_id": "SKL-999", "proficiency": 2}],
        headers=auth(s_token),
    ).status_code == 400

    # --- job posting -------------------------------------------------------
    job = envelope(
        client.post(
            "/api/jobs",
            json={
                "title": "Backend Intern",
                "description": "Build FastAPI services for our platform.",
                "type": "internship",
                "min_cgpa": 7.0,
                "required_skills": [
                    {"skill_id": "SKL-101", "required_proficiency": 3},
                    {"skill_id": "SKL-402", "required_proficiency": 3, "is_mandatory": False},
                ],
            },
            headers=auth(r_token),
        )
    )["data"]
    assert len(job["required_skills"]) == 2

    # students cannot post jobs
    assert client.post(
        "/api/jobs",
        json={"title": "Fake", "description": "not allowed at all", "required_skills": []},
        headers=auth(s_token),
    ).status_code == 403

    listed = envelope(client.get("/api/jobs", params={"skill_id": "SKL-101"}, headers=auth(s_token)))["data"]
    assert [j["id"] for j in listed] == [job["id"]]

    # --- application flow --------------------------------------------------
    application = envelope(
        client.post("/api/applications", json={"job_id": job["id"]}, headers=auth(s_token))
    )["data"]
    assert application["status"] == "applied"
    assert client.post("/api/applications", json={"job_id": job["id"]}, headers=auth(s_token)).status_code == 409

    # matching engine writes the score, recruiter sees the ranked list
    client.patch(f"/api/applications/{application['id']}/score", json={"match_score": 91.5}, headers=auth(r_token))
    applicants = envelope(client.get(f"/api/applications/job/{job['id']}", headers=auth(r_token)))["data"]
    assert applicants[0]["match_score"] == 91.5
    assert applicants[0]["student"]["name"] == "Asha Rao"

    shortlisted = envelope(
        client.patch(f"/api/applications/{application['id']}/status", json={"status": "shortlisted"}, headers=auth(r_token))
    )["data"]
    assert shortlisted["status"] == "shortlisted"

    # --- skill gaps & readiness score --------------------------------------
    gaps = envelope(
        client.put(
            f"/api/students/{student['user']['id']}/gaps",
            json=[{"skill_id": "SKL-402", "job_id": job["id"], "current_proficiency": 0, "required_proficiency": 3, "priority": 9.0}],
            headers=auth(s_token),
        )
    )["data"]
    assert gaps[0]["skill"]["canonical_name"] == "PostgreSQL"

    client.patch(f"/api/students/{student['user']['id']}/score", json={"readiness_score": 76.0}, headers=auth(s_token))
    assert envelope(client.get("/api/students/me", headers=auth(s_token)))["data"]["readiness_score"] == 76.0

    # --- resume upload -----------------------------------------------------
    pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
    uploaded = envelope(
        client.post("/api/uploads/resume", files={"file": ("cv.pdf", pdf, "application/pdf")}, headers=auth(s_token))
    )["data"]
    assert uploaded["resume_url"].endswith(str(student["user"]["id"]))

    # non-PDF content is rejected even with a .pdf extension
    assert client.post(
        "/api/uploads/resume",
        files={"file": ("evil.pdf", b"<?php echo 1; ?>", "application/pdf")},
        headers=auth(s_token),
    ).status_code == 400

    path = envelope(client.get(f"/api/uploads/resume/{student['user']['id']}/path", headers=auth(s_token)))["data"]["path"]
    assert Path(path).read_bytes() == pdf

    # a second student cannot read the first one's resume or profile
    other = envelope(
        client.post(
            "/api/auth/register",
            json={"email": "b@c.edu", "password": "SuperSecret1", "role": "student", "name": "Bee"},
        )
    )["data"]
    assert client.get(f"/api/uploads/resume/{student['user']['id']}", headers=auth(other["access_token"])).status_code == 403
    assert client.get(f"/api/students/{student['user']['id']}", headers=auth(other["access_token"])).status_code == 403
    # ...but a recruiter can
    assert client.get(f"/api/students/{student['user']['id']}", headers=auth(r_token)).status_code == 200


def test_error_envelope(client):
    body = envelope(client.post("/api/auth/register", json={"email": "not-an-email", "password": "x"}))
    assert body["status"] == "error" and body["errors"]
