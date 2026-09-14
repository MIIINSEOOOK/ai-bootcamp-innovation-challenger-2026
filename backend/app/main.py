from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.analysis.engines import AnalysisCoordinator, RuleAssessmentEngine
from app.api.routes import create_api_router
from app.repositories.json_repository import JsonDataRepository
from app.services.application_service import ApplicationService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
load_dotenv(BACKEND_ROOT / ".env", override=True)


def create_app(
    *,
    data_path: Path | None = None,
    personas_path: Path | None = None,
    rules_path: Path | None = None,
) -> FastAPI:
    configured_data_path = os.getenv("APP_DATA_PATH")
    resolved_data_path = data_path or (Path(configured_data_path) if configured_data_path else BACKEND_ROOT / "data" / "app_data.json")
    resolved_personas_path = personas_path or PROJECT_ROOT / "data" / "personas" / "personas.json"
    resolved_rules_path = rules_path or BACKEND_ROOT / "config" / "analysis_rules.json"

    repository = JsonDataRepository(resolved_data_path)
    coordinator = AnalysisCoordinator(RuleAssessmentEngine(resolved_rules_path))
    service = ApplicationService(repository, coordinator, resolved_personas_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await service.initialize()
        yield

    app = FastAPI(
        title="자립동행 MVP API",
        version="1.0.0",
        description="로컬 JSON 저장소 기반 자립준비청년 안전망 감지 데모 API",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8443", "http://127.0.0.1:8443"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_api_router(service))
    app.state.repository = repository
    app.state.service = service
    return app


app = create_app()
