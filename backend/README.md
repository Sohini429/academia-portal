# Academia–Industry Collaboration Portal — Backend Service

**SIH Problem Statement 26044 · Member 2 deliverable — Backend, Database & Authentication Engineer**

FastAPI + PostgreSQL service providing the database schema, JWT authentication,
the Master Skill Registry, the REST API surface and resume file handling that
the other four modules build on.

---

## 1. Quick start

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit DATABASE_URL and JWT_SECRET
python seed_skills.py         # loads the 78-skill Master Skill Registry
uvicorn app.main:app --reload --port 8000
```

* Interactive docs: <http://localhost:8000/docs>
* Health check: `GET /api/health`

No local PostgreSQL? Set `DATABASE_URL=sqlite:///./portal.db` in `.env`. The code
is database-agnostic; PostgreSQL is the production target.

Run the end-to-end test suite (uses a throwaway SQLite file, no setup needed):

```bash
pytest -q
```

---

## 2. Database schema

Tables are created automatically on startup. Every skill reference anywhere in
the system is a **canonical Skill ID** (`SKL-101`), never a raw string.

| Table | Primary key | Key columns | Purpose |
|---|---|---|---|
| `users` | `id` | `email`, `password_hash`, `role` (`student`/`college`/`industry`), `is_active` | Central authentication & identity |
| `colleges` | `user_id` → `users.id` | `name`, `city`, `university` | Institution profile |
| `companies` | `user_id` → `users.id` | `name`, `industry`, `website` | Recruiter/company profile |
| `students` | `user_id` → `users.id` | `name`, `college_id`, `branch`, `cgpa`, `github_url`, `resume_url`, `resume_path`, `readiness_score` | Student profile |
| `skills` | `id` (`SKL-101`) | `canonical_name`, `category`, `parent_skill_id` | **Master Skill Registry — single source of truth** |
| `skill_aliases` | `id` | `skill_id`, `alias` | Alternate spellings (`py`, `python3`) for the AI engine's fast lookup |
| `student_skills` | (`student_id`, `skill_id`) | `proficiency` 1–5, `source`, `verified` | Student proficiency per canonical skill |
| `jobs` | `id` | `company_id`, `title`, `description`, `location`, `type`, `min_cgpa`, `is_open` | Job & internship postings |
| `job_skills` | (`job_id`, `skill_id`) | `required_proficiency` 1–5, `is_mandatory`, `weight` | Mandatory/optional job skill requirements |
| `applications` | `id` | `student_id`, `job_id`, `status`, `match_score` | Placement applications |
| `skill_gaps` | `id` | `student_id`, `skill_id`, `job_id`, `current_proficiency`, `required_proficiency`, `priority` | Gap report written by the matching engine |

Integrity is enforced in the database, not in application code: `CHECK`
constraints on roles, statuses, job types and 1–5 proficiency ranges; a
`UNIQUE` constraint stopping duplicate applications; `ON DELETE CASCADE` on
every ownership edge.

---

## 3. Standard payload contract

Every response — success or failure — uses the wrapper agreed in the manual:

```json
{
  "status": "success",
  "data":   { "...": "requested resource" },
  "timestamp": "2026-09-10T09:15:22.431117+00:00",
  "errors": null
}
```

Failures return `"status": "error"`, `"data": null` and `errors` as an array of
strings. Validation failures (HTTP 422) list one entry per invalid field.

---

## 4. Authentication

JWT bearer tokens, HS256. `POST /api/auth/login` returns an **access token**
(30 min) and a **refresh token** (7 days); tokens carry `sub`, `role` and
`type`, and a refresh token is rejected wherever an access token is required.
Passwords are hashed with bcrypt and never returned by any endpoint. Login
returns the same message for an unknown email and a wrong password, so the API
cannot be used to enumerate accounts.

Send the token as `Authorization: Bearer <access_token>`.

### Role matrix

| Capability | student | college | industry |
|---|:--:|:--:|:--:|
| Read skill registry | ✔ | ✔ | ✔ |
| Add a skill to the registry | — | ✔ | ✔ |
| Read/edit own student profile, skills, gaps | ✔ | — | — |
| Read any student profile & resume | own only | ✔ | ✔ |
| Create/edit/delete job postings | — | — | own only |
| Browse open jobs | ✔ | ✔ | ✔ |
| Apply to a job | ✔ | — | — |
| View applicants, set application status | — | — | own postings |

---

## 5. API reference

### Auth — `/api/auth`
| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/register` | public | Create a user plus their role profile; returns a token pair |
| POST | `/login` | public | Email + password → token pair |
| POST | `/refresh` | public | Refresh token → new token pair |
| GET | `/me` | any | Current identity |

### Master Skill Registry — `/api/skills`
| Method | Path | Access | Description |
|---|---|---|---|
| GET | `` | public | Autocomplete search (`?q=`, `?category=`, `?limit=`) — powers all frontend skill dropdowns |
| GET | `/categories` | public | Distinct categories |
| POST | `/resolve` | public | `{"terms": ["Py", "postgres"]}` → `{"matched": {"Py": "SKL-101", ...}, "unmatched": [...]}` |
| GET | `/{skill_id}` | public | One skill with its aliases |
| POST | `` | college, industry | Register a new canonical skill |

### Students — `/api/students`
| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/me` | student | Own profile with skills |
| PATCH | `/me` | student | Update profile fields |
| GET | `/{student_id}` | owner, college, industry | Profile with skills |
| GET | `/{student_id}/skills` | owner, college, industry | Skill list |
| PUT | `/{student_id}/skills` | owner | Add/update skills — also the AI engine's write path (`source: "resume"`); keeps the higher proficiency on conflict |
| DELETE | `/{student_id}/skills/{skill_id}` | owner | Remove a skill |
| GET | `/{student_id}/gaps` | owner, college, industry | Gap report, highest priority first |
| PUT | `/{student_id}/gaps` | owner | Replace the whole gap report (matching engine) |
| PATCH | `/{student_id}/score` | owner | Store the Employability Readiness Score (0–100) |

### Jobs — `/api/jobs`
| Method | Path | Access | Description |
|---|---|---|---|
| GET | `` | any | Browse jobs (`?skill_id=`, `?location=`, `?type=`, `?open_only=`, `?limit=`, `?offset=`) |
| GET | `/mine` | industry | Own postings |
| GET | `/{job_id}` | any | One job with company and required skills |
| POST | `` | industry | Create a posting with its required Skill IDs |
| PATCH | `/{job_id}` | owner | Update fields; sending `required_skills` replaces the set |
| DELETE | `/{job_id}` | owner | Delete a posting |

### Applications — `/api/applications`
| Method | Path | Access | Description |
|---|---|---|---|
| POST | `` | student | Apply (rejects duplicates, closed postings and CGPA shortfalls) |
| GET | `/mine` | student | Own applications with job details |
| GET | `/job/{job_id}` | owner recruiter | Applicants sorted by match score, highest first |
| PATCH | `/{application_id}/status` | owner recruiter | `applied` → `shortlisted`/`rejected`/`hired` |
| PATCH | `/{application_id}/score` | matching engine | Store the computed match percentage |

### Resume files — `/api/uploads`
| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/resume` | student | Multipart PDF upload (max 5 MB) |
| GET | `/resume/{student_id}` | owner, college, industry | Download the PDF |
| GET | `/resume/{student_id}/path` | owner, college, industry | Absolute server path, for the AI parsing pipeline |
| DELETE | `/resume` | student | Delete own resume |

Uploads are validated by extension **and** by PDF magic bytes, stored under a
server-generated UUID filename outside any served directory, and capped in
size. The client never controls the storage path, so a malicious filename
cannot escape the upload directory.

---

## 6. Integration notes for the other modules

* **Member 1 (Frontend):** populate every skill input from `GET /api/skills?q=`
  and submit Skill IDs. Store both tokens; on a 401 call `/api/auth/refresh`
  before retrying.
* **Member 3 (AI/NLP):** read the resume from
  `GET /api/uploads/resume/{id}/path`, map extracted terms through
  `POST /api/skills/resolve`, then write results with
  `PUT /api/students/{id}/skills` using `source: "resume"`.
* **Member 4 (Industry/College dashboards):** post jobs with Skill IDs and
  proficiencies; read candidates from `GET /api/applications/job/{id}`.
* **Member 5 (Matching engine):** read `student_skills` and `job_skills` through
  the API, then write back with `PATCH /api/applications/{id}/score`,
  `PATCH /api/students/{id}/score` and `PUT /api/students/{id}/gaps`.

---

## 7. Layout

```
backend/
├── app/
│   ├── config.py        # env-driven settings
│   ├── database.py      # engine, session, declarative base
│   ├── models.py        # all 11 tables
│   ├── schemas.py       # request/response contracts
│   ├── security.py      # bcrypt, JWT, role dependencies
│   ├── responses.py     # standard payload envelope + error handlers
│   ├── main.py          # app assembly, CORS, routers
│   └── routers/         # auth, skills, students, jobs, applications, uploads
├── seed_skills.py       # Master Skill Registry seed (78 skills, idempotent)
├── tests/test_api.py    # end-to-end journey: register → skills → job → apply → score
├── requirements.txt
└── .env.example
```

## 8. Deliberate scope limits

* Schema is created with `create_all` on startup. Introduce Alembic migrations
  once the schema changes after first deployment.
* Refresh tokens are stateless. Add a revocation table if forced logout or
  token blacklisting becomes a requirement.
* Resume storage is local disk. Swap `app/routers/uploads.py` for S3 when the
  service runs on more than one instance.
