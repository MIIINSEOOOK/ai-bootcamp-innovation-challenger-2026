from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth.demo import get_current_user, login_demo_user
from app.schemas.models import (
    AlertRecord,
    AlertUpdate,
    AnalysisRequest,
    AssessmentRecord,
    CaseActionCreate,
    CaseActionRecord,
    CheckinCreate,
    CheckinRecord,
    DemoUser,
    LoginRequest,
    LoginResponse,
    YouthDetail,
    YouthListItem,
)
from app.services.application_service import ApplicationService


class HealthResponse(BaseModel):
    status: str
    storage: str
    demoMode: bool


class CheckinSubmissionResponse(BaseModel):
    checkin: CheckinRecord
    assessment: AssessmentRecord


def create_api_router(service: ApplicationService) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", storage="json", demoMode=True)

    @router.post("/auth/login", response_model=LoginResponse)
    def login(request: LoginRequest) -> LoginResponse:
        return login_demo_user(request)

    @router.get("/auth/me", response_model=DemoUser)
    def me(user: DemoUser = Depends(get_current_user)) -> DemoUser:
        return user

    @router.get("/youths", response_model=list[YouthListItem])
    def youths(
        query: str | None = Query(default=None),
        status_label: str | None = Query(default=None, alias="status"),
        user: DemoUser = Depends(get_current_user),
    ) -> list[YouthListItem]:
        return service.list_youths(query=query, label=status_label)

    @router.get("/youths/{youth_id}", response_model=YouthDetail)
    def youth_detail(youth_id: str, user: DemoUser = Depends(get_current_user)) -> YouthDetail:
        return service.get_youth_detail(youth_id)

    @router.get("/youths/{youth_id}/checkins", response_model=list[CheckinRecord])
    def youth_checkins(youth_id: str, user: DemoUser = Depends(get_current_user)) -> list[CheckinRecord]:
        return service.get_checkins(youth_id)

    @router.post("/checkins", response_model=CheckinSubmissionResponse)
    async def create_checkin(
        request: CheckinCreate,
        user: DemoUser = Depends(get_current_user),
    ) -> CheckinSubmissionResponse:
        checkin, assessment = await service.create_checkin(request)
        return CheckinSubmissionResponse(checkin=checkin, assessment=assessment)

    @router.get("/alerts", response_model=list[AlertRecord])
    def alerts(user: DemoUser = Depends(get_current_user)) -> list[AlertRecord]:
        return service.list_alerts()

    @router.patch("/alerts/{alert_id}", response_model=AlertRecord)
    def update_alert(
        alert_id: str,
        request: AlertUpdate,
        user: DemoUser = Depends(get_current_user),
    ) -> AlertRecord:
        return service.update_alert(alert_id, request)

    @router.get("/youths/{youth_id}/actions", response_model=list[CaseActionRecord])
    def actions(youth_id: str, user: DemoUser = Depends(get_current_user)) -> list[CaseActionRecord]:
        return service.get_actions(youth_id)

    @router.post("/youths/{youth_id}/actions", response_model=CaseActionRecord)
    def create_action(
        youth_id: str,
        request: CaseActionCreate,
        user: DemoUser = Depends(get_current_user),
    ) -> CaseActionRecord:
        return service.create_action(youth_id, request, user)

    @router.post("/youths/{youth_id}/analyze", response_model=AssessmentRecord)
    async def analyze(
        youth_id: str,
        request: AnalysisRequest,
        user: DemoUser = Depends(get_current_user),
    ) -> AssessmentRecord:
        return await service.analyze_youth(youth_id, mode=request.mode)

    return router
