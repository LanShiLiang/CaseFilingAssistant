from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.application import confirm_generation as confirm_generation_use_case
from app.application import get_generation_artifact, run_validation
from app.application import start_generation as start_generation_use_case
from app.config import Settings, get_settings
from app.database import Base, Database
from app.errors import DomainError
from app.extraction import image_ocr_available
from app.health import worker_health
from app.models import Generation, Job, Matter
from app.schemas import (
    CapabilityResponse,
    CreateMatterRequest,
    GenerationResponse,
    GenerationStartResponse,
    JobResponse,
    MatterResponse,
    RevisionRequest,
    SaveFactsRequest,
    UploadResponse,
    ValidationResponse,
)
from app.services import (
    create_matter,
    generation_to_response,
    get_matter,
    job_to_response,
    matter_to_response,
    save_confirmed_facts,
    upload_document,
)
from app.storage import LocalBlobStore

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    database = Database(resolved)
    store = LocalBlobStore(resolved.storage_root)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        resolved.storage_root.mkdir(parents=True, exist_ok=True)
        if resolved.environment == "test":
            Base.metadata.create_all(database.engine)
        yield
        database.engine.dispose()

    app = FastAPI(
        title="Case Filing Assistant API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.settings = resolved
    app.state.database = database
    app.state.store = store
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store, private"
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request.state.request_id,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "request_validation_failed",
                    "message": "请求字段格式不正确。",
                    "request_id": request.state.request_id,
                    "details": {"errors": exc.errors()},
                }
            },
        )

    def session_dependency() -> Session:
        yield from database.session()

    @app.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def health_ready(session: Session = Depends(session_dependency)) -> dict[str, str]:
        session.execute(text("SELECT 1"))
        if not store.is_writable():
            raise DomainError("storage_unavailable", "本地存储不可写。", 503)
        return {"status": "ready"}

    @app.get("/api/v1/capabilities", response_model=CapabilityResponse)
    def capabilities(session: Session = Depends(session_dependency)) -> CapabilityResponse:
        session.execute(text("SELECT 1"))
        worker_available, worker_reason = worker_health(resolved)
        return CapabilityResponse(
            database=True,
            storage=store.is_writable(),
            worker=worker_available,
            worker_reason=worker_reason,
            image_ocr=image_ocr_available(),
        )

    @app.post("/api/v1/matters", response_model=MatterResponse, status_code=201)
    def create_matter_route(
        payload: CreateMatterRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        session: Session = Depends(session_dependency),
    ) -> MatterResponse:
        return create_matter(
            session,
            eligibility_confirmed=payload.eligibility_confirmed,
            eligibility_version=payload.eligibility_version,
            idempotency_key=idempotency_key,
        )

    @app.get("/api/v1/matters", response_model=list[MatterResponse])
    def list_matters(session: Session = Depends(session_dependency)) -> list[MatterResponse]:
        matters = session.scalars(
            select(Matter)
            .options(selectinload(Matter.documents), selectinload(Matter.generations))
            .order_by(Matter.updated_at.desc())
            .limit(20)
        ).all()
        return [matter_to_response(item) for item in matters]

    @app.get("/api/v1/matters/{matter_id}", response_model=MatterResponse)
    def get_matter_route(
        matter_id: str, session: Session = Depends(session_dependency)
    ) -> MatterResponse:
        return matter_to_response(get_matter(session, matter_id))

    @app.post("/api/v1/matters/{matter_id}/documents", response_model=UploadResponse)
    def upload_document_route(
        matter_id: str,
        kind: str = Form(...),
        expected_revision: int = Form(...),
        file: UploadFile = File(...),
        session: Session = Depends(session_dependency),
    ) -> UploadResponse:
        document, job, revision = upload_document(
            session, store, resolved, matter_id, kind, expected_revision, file
        )
        return UploadResponse(document=document, job_id=job.id, revision=revision)

    @app.put("/api/v1/matters/{matter_id}/facts", response_model=MatterResponse)
    def save_facts_route(
        matter_id: str,
        payload: SaveFactsRequest,
        session: Session = Depends(session_dependency),
    ) -> MatterResponse:
        return save_confirmed_facts(
            session,
            matter_id,
            payload.expected_revision,
            payload.fields,
            payload.confirm_fields,
        )

    @app.post("/api/v1/matters/{matter_id}/validate", response_model=ValidationResponse)
    def validate_route(
        matter_id: str,
        payload: RevisionRequest,
        session: Session = Depends(session_dependency),
    ) -> ValidationResponse:
        return run_validation(
            session, matter_id, payload.expected_revision, resolved
        )

    @app.post(
        "/api/v1/matters/{matter_id}/generations",
        response_model=GenerationStartResponse,
        status_code=202,
    )
    def start_generation(
        matter_id: str,
        payload: RevisionRequest,
        session: Session = Depends(session_dependency),
    ) -> GenerationStartResponse:
        return start_generation_use_case(
            session, matter_id, payload.expected_revision, resolved
        )

    @app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
    def get_job(job_id: str, session: Session = Depends(session_dependency)) -> JobResponse:
        job = session.get(Job, job_id)
        if not job:
            raise DomainError("job_not_found", "任务不存在。", 404)
        return job_to_response(job)

    @app.get("/api/v1/generations/{generation_id}", response_model=GenerationResponse)
    def get_generation(
        generation_id: str, session: Session = Depends(session_dependency)
    ) -> GenerationResponse:
        generation = session.get(Generation, generation_id)
        if not generation:
            raise DomainError("generation_not_found", "生成记录不存在。", 404)
        matter = get_matter(session, generation.matter_id)
        return generation_to_response(generation, matter.revision)

    @app.post("/api/v1/generations/{generation_id}/confirm", response_model=GenerationResponse)
    def confirm_generation(
        generation_id: str,
        payload: RevisionRequest,
        session: Session = Depends(session_dependency),
    ) -> GenerationResponse:
        return confirm_generation_use_case(
            session, generation_id, payload.expected_revision
        )

    @app.get("/api/v1/generations/{generation_id}/preview")
    def preview_generation(
        generation_id: str, session: Session = Depends(session_dependency)
    ) -> FileResponse:
        artifact = get_generation_artifact(
            session, store, generation_id, kind="preview"
        )
        return FileResponse(
            artifact.path,
            media_type=artifact.media_type,
            filename=artifact.filename,
        )

    @app.get("/api/v1/generations/{generation_id}/download")
    def download_generation(
        generation_id: str, session: Session = Depends(session_dependency)
    ) -> FileResponse:
        artifact = get_generation_artifact(
            session, store, generation_id, kind="download"
        )
        return FileResponse(
            artifact.path,
            media_type=artifact.media_type,
            filename=artifact.filename,
        )

    return app


app = create_app()
