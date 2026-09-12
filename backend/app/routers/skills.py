"""Master Skill Registry endpoints - the single source of truth for Skill IDs."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Skill, SkillAlias
from ..responses import ok
from ..schemas import SkillCreate, SkillOut, SkillResolveRequest
from ..security import require_role

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
def list_skills(
    q: str | None = Query(default=None, description="Autocomplete prefix/substring"),
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Feeds the frontend's autocomplete dropdowns. Public: needed on signup forms."""
    stmt = select(Skill)
    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.outerjoin(SkillAlias).where(
            func.lower(Skill.canonical_name).like(pattern) | func.lower(SkillAlias.alias).like(pattern)
        )
    if category:
        stmt = stmt.where(Skill.category == category)
    skills = db.scalars(stmt.distinct().order_by(Skill.canonical_name).limit(limit)).all()
    return ok([SkillOut.model_validate(s) for s in skills])


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    return ok(sorted(db.scalars(select(Skill.category).distinct()).all()))


@router.post("/resolve")
def resolve_terms(payload: SkillResolveRequest, db: Session = Depends(get_db)):
    """Map raw resume/job-description terms onto canonical Skill IDs.

    Exact, case-insensitive match on canonical name or alias. Fuzzy/semantic
    matching is the AI engine's job (Member 3); this is the authoritative lookup
    it falls back to.
    """
    lookup: dict[str, str] = {}
    for skill in db.scalars(select(Skill).options(selectinload(Skill.aliases))):
        lookup[skill.canonical_name.lower()] = skill.id
        for alias in skill.aliases:
            lookup[alias.alias.lower()] = skill.id

    matched, unmatched = {}, []
    for term in payload.terms:
        skill_id = lookup.get(term.strip().lower())
        if skill_id:
            matched[term] = skill_id
        else:
            unmatched.append(term)
    return ok({"matched": matched, "unmatched": unmatched})


@router.get("/{skill_id}")
def get_skill(skill_id: str, db: Session = Depends(get_db)):
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown skill id: {skill_id}")
    data = SkillOut.model_validate(skill).model_dump()
    data["aliases"] = [a.alias for a in skill.aliases]
    return ok(data)


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("college", "industry"))])
def create_skill(payload: SkillCreate, db: Session = Depends(get_db)):
    """Registry additions are restricted; students never mint new Skill IDs."""
    if db.get(Skill, payload.id):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Skill {payload.id} already exists")
    if payload.parent_skill_id and not db.get(Skill, payload.parent_skill_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown parent_skill_id")

    skill = Skill(**payload.model_dump(exclude={"aliases"}))
    skill.aliases = [SkillAlias(alias=a.strip().lower()) for a in payload.aliases]
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return ok(SkillOut.model_validate(skill))
