# Member 5 - Skill Matching, Recommendation & Integration

This folder contains the Member 5 prototype for the Academia-Industry Collaboration Portal.

## Included
- Skill match percentage engine
- Skill gap identification and priority
- Learning/certification/internship recommendations
- Industry skill demand aggregation
- Employability readiness score
- FastAPI integration endpoints
- Basic tests

## Run

Open terminal in this folder:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Important integration note

The current prototype uses sample Skill IDs such as SKL-101. During team integration, replace sample data with the canonical Skill IDs and database/API data supplied by Member 2 and the standardized extraction output from Member 3.

Do not create a second Skill Registry.
