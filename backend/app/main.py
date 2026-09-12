"""Academia-Industry Collaboration Portal - backend service (Member 2)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .responses import http_exception_handler, ok, validation_exception_handler
from .routers import applications, auth, jobs, skills, students, uploads

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # ponytail: create_all is enough for a single-service demo schema.
    # Switch to Alembic migrations once the schema changes after deployment.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Academia-Industry Collaboration Portal API",
    description="Authentication, Master Skill Registry, profiles, jobs and applications.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

for router in (auth, skills, students, jobs, applications, uploads):
    app.include_router(router.router)


@app.get("/api/health", tags=["meta"])
def health():
    return ok({"service": "portal-backend", "database": engine.url.get_backend_name()})
