# Academia Portal - Integration Guide

## Project Overview

The Academia Portal is a multi-stage skill extraction and matching system that processes student resumes (PDFs) and extracts standardized skill IDs for database storage.

**Architecture:** Backend (FastAPI) + Frontend (Student/Industry Views) + AI Engine (NLP Pipeline)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ACADEMIA PORTAL                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  FRONTEND (React.js)                                              │
│  ├── /student         → Student Dashboard                        │
│  └── /industry        → Industry/Recruiter Portal                │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  BACKEND (FastAPI + PostgreSQL)                                  │
│  ├── /app             → API Endpoints & Routes                   │
│  ├── /core            → Database Models & Config                 │
│  ├── /ai_engine       → Skill Extraction Pipeline                │
│  └── /match_engine    → Skill Matching Logic                     │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  AI PROCESSING (Root Level)                                      │
│  ├── pdf_extractor.py      → Step 2: PDF Text Extraction        │
│  ├── alias_matcher.py      → Step 3: Stage 1 (Regex/Alias)      │
│  ├── nlp_matcher.py        → Step 4: Stage 2 (NLP/Semantic)     │
│  ├── pipeline.py           → Step 5: Full Pipeline              │
│  └── fastapi_async_example.py → Step 6: Async Integration       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. **PDF Extraction Layer** (`pdf_extractor.py`)

**Purpose:** Extract clean text from resume PDFs

**Key Features:**
- Uses `pdfplumber` for robust PDF handling (better with columns/tables)
- Removes null bytes and stray characters
- Handles multi-page documents

**Output:** Clean text string ready for skill extraction

```python
# Input: Resume PDF path
# Output: Extracted text (string)
text = extract_text_from_pdf("resume.pdf")
```

**Dependencies:** `pdfplumber`

---

### 2. **Stage 1: Alias Matcher** (`alias_matcher.py`)

**Purpose:** Fast regex-based skill lookup (60-70% accuracy)

**Key Components:**

1. **`load_registry(path)`** - Loads master skill registry from JSON
2. **`build_alias_map(registry)`** - Creates lowercase alias → skill_id mapping
3. **`stage1_match(text, alias_map)`** - Searches known aliases in text

**Example Skill Registry:**
```json
{
  "id": "SKL-101",
  "canonical_name": "Python",
  "aliases": ["py", "python3", "python 3"]
}
```

**Golden Rule:** Always match against skill IDs, never store raw text

**Dependencies:** `re` (built-in)

---

### 3. **Stage 2: NLP Matcher** (`nlp_matcher.py`)

**Purpose:** Semantic matching for skills missed by Stage 1

**Key Components:**

1. **`extract_candidate_phrases(text)`**
   - Uses spaCy to extract noun phrases
   - Filters by length (2-40 chars)

2. **`stage2_match(candidates, registry, threshold=0.75)`**
   - Encodes phrases using Sentence-Transformers
   - Calculates cosine similarity with canonical skill names
   - Returns matched skill IDs above threshold

**Performance Notes:**
- Models loaded once at startup (not per request)
- Threshold tuning is critical (0.75 default, adjust for precision/recall)

**Dependencies:** `spacy`, `sentence-transformers`

---

### 4. **Pipeline** (`pipeline.py`)

**Purpose:** Unified entry point combining Stage 1 + Stage 2

**Function:** `run_pipeline(pdf_path, registry_path) → dict`

**Flow:**
```
1. Load registry and build alias map
2. Extract text from PDF
3. Run Stage 1 (alias matching)
4. Run Stage 2 (NLP matching)
5. Merge results (union of both stage IDs)
6. Return: skill_ids + unmatched_terms
```

**Output Format:**
```json
{
  "status": "success",
  "data": {
    "skill_ids": ["SKL-101", "SKL-103", "SKL-104"]
  },
  "unmatched_terms": [("deep learning", 0.72), ...],
  "errors": null
}
```

**Golden Rule:** Unmatched terms logged for review, NEVER stored in database

---

### 5. **FastAPI Async Integration** (`fastapi_async_example.py`)

**Purpose:** Non-blocking resume upload with background processing

**Endpoint:** `POST /resume/upload`

**Parameters:**
- `student_id` (str)
- `file` (UploadFile)

**Workflow:**
```
1. Save uploaded PDF to temp storage
2. Return success immediately to client
3. Process in background (async task)
4. Extract skill IDs
5. Save to database (TODO: Student Skills table)
```

**Key Benefit:** User gets instant feedback while extraction happens background

**Dependencies:** `fastapi`, `uvicorn`, `python-multipart`

---

## Backend Structure (`/backend`)

### Key Directories

- **`/app`** - FastAPI application routes and endpoints
- **`/core`** - Database models, config, settings
- **`/ai_engine`** - Skill extraction pipeline integration
- **`/match_engine`** - Matching logic and skill comparisons
- **`/tests`** - Unit tests for API and core logic

### Key Files

- **`seed_skills.py`** - Database initialization with skill registry
- **`requirements.txt`** - Backend dependencies

**Backend Dependencies:**
```
fastapi~=0.115
uvicorn[standard]~=0.34
sqlalchemy~=2.0
psycopg[binary]~=3.2
pydantic~=2.10
pydantic-settings~=2.7
email-validator~=2.2
python-multipart~=0.0.20
pyjwt~=2.10
bcrypt~=4.2
httpx~=0.28
pytest~=8.3
```

---

## Frontend Structure (`/frontend`)

### Key Directories

- **`/student`** - Student dashboard and profile views
- **`/industry`** - Industry/recruiter portal views

### Responsibilities

- Upload resume UI
- Display extracted skills
- Manage student profile
- Browse candidates (for industry users)

---

## Data Flow Diagram

```
┌──────────────────────┐
│  Upload Resume (PDF) │
└���─────────┬───────────┘
           │
           ▼
┌──────────────────────────┐
│ FastAPI Endpoint         │
│ /resume/upload           │
└──────────┬───────────────┘
           │
           ├─► Save to /tmp
           │
           └─► Add Background Task
               │
               ▼
    ┌─────────────────────────────┐
    │  pipeline.run_pipeline()    │
    │  (Background Task)          │
    └──────────┬──────────────────┘
               │
               ├─► pdf_extractor.extract_text_from_pdf()
               │   └─► Raw text extracted
               │
               ├─► alias_matcher.stage1_match()
               │   └─► Known skills (60-70%)
               │
               ├─► nlp_matcher.stage2_match()
               │   └─► Semantic skills
               │
               └─► Merge Results (Union)
                   │
                   ▼
        ┌──────────────────────────────┐
        │ skill_ids = {SKL-101, ...}   │
        │ unmatched_terms = [...]      │
        └──────────┬───────────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │ Save to student_skills table │
        │ (Member 2: Backend Database) │
        └──────────────────────────────┘
```

---

## Integration Checklist

### ✅ Phase 1: Backend Setup
- [ ] Initialize FastAPI application in `/app`
- [ ] Create database models in `/core`:
  - [ ] Students table
  - [ ] Skills registry table
  - [ ] Student_Skills junction table
- [ ] Set up PostgreSQL connection (psycopg)
- [ ] Create `/resume/upload` endpoint

### ✅ Phase 2: AI Engine Integration
- [ ] Copy root-level AI scripts to `/ai_engine`:
  - [ ] `pdf_extractor.py`
  - [ ] `alias_matcher.py`
  - [ ] `nlp_matcher.py`
  - [ ] `pipeline.py`
- [ ] Download spaCy model: `python -m spacy download en_core_web_sm`
- [ ] Test pipeline with sample resume

### ✅ Phase 3: Async Background Tasks
- [ ] Implement FastAPI background tasks in `/app`
- [ ] Connect `pipeline.run_pipeline()` to database insert
- [ ] Update Student_Skills table on extraction completion

### ✅ Phase 4: Frontend Integration
- [ ] Build `/student` resume upload UI
- [ ] Create skills display component
- [ ] Build `/industry` recruiter search interface
- [ ] Connect frontend to backend API endpoints

### ✅ Phase 5: Database Seeding
- [ ] Run `backend/seed_skills.py` to populate skill registry
- [ ] Verify skills loaded correctly

### ✅ Phase 6: Testing
- [ ] Unit tests for PDF extraction
- [ ] Unit tests for Stage 1 (alias matching)
- [ ] Unit tests for Stage 2 (NLP matching)
- [ ] Integration tests for full pipeline
- [ ] API endpoint tests

---

## Configuration & Settings

### Skills Registry (`skills_registry_sample.json`)

**Schema:**
```json
{
  "id": "SKL-XXX",                    // Unique skill ID
  "canonical_name": "Skill Name",     // Standard name
  "category": "Category",              // Classification
  "aliases": ["alt1", "alt2"]         // Common variations
}
```

### Environment Variables (Backend)

```env
DATABASE_URL=postgresql://user:pass@localhost/academia_db
JWT_SECRET=your-secret-key
SKILL_REGISTRY_PATH=./skills_registry.json
NLP_MODEL=en_core_web_sm
EMBEDDING_MODEL=all-MiniLM-L6-v2
SIMILARITY_THRESHOLD=0.75
```

---

## Key Design Principles

### 1. **Two-Stage Matching**
   - **Stage 1 (Fast):** Regex alias lookup → 60-70% recall
   - **Stage 2 (Smart):** NLP semantic matching → catches nuanced variations

### 2. **Golden Rule: Only Skill IDs in Database**
   - Never store raw extracted text
   - Always normalize to canonical skill IDs
   - Unmatched terms logged for review, not persisted

### 3. **Non-Blocking Uploads**
   - Async background processing
   - Instant response to user
   - Prevents timeout on large PDFs

### 4. **Configurable Thresholds**
   - NLP similarity threshold tunable per deployment
   - Trade-off: Precision vs. Recall

---

## Dependencies Summary

### Root Level (AI Processing)
- `pdfplumber` - PDF text extraction
- `spacy` - NLP (noun phrase extraction)
- `sentence-transformers` - Semantic similarity
- `fastapi`, `uvicorn` - Web framework
- `python-multipart` - File upload handling

### Backend
- All root-level + PostgreSQL drivers
- `sqlalchemy` - ORM
- `pydantic` - Data validation
- `pyjwt`, `bcrypt` - Authentication
- `pytest` - Testing

### Installation
```bash
# Root AI pipeline
pip install -r requirements.txt

# Backend (includes AI pipeline)
pip install -r backend/requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

---

## Next Steps

1. **Backend Development:** Implement database schema and API endpoints
2. **AI Integration:** Move AI scripts to `/backend/ai_engine` and test
3. **Frontend:** Build upload and display components
4. **Testing:** Comprehensive test suite for each stage
5. **Deployment:** Containerization (Docker) and CI/CD setup

---

## Support & Documentation

- **Backend README:** `backend/README.md`
- **Sample Registry:** `skills_registry_sample.json`
- **Example Integration:** `fastapi_async_example.py`
- **Data Sample:** `m resume.pdf` (test file)

---

**Last Updated:** 2026-09-14  
**Status:** Integration Guide v1.0
