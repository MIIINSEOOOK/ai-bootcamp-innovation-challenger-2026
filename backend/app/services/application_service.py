from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.analysis.engines import AnalysisCoordinator
from app.repositories.base import DataRepository
from app.schemas.models import (
    AlertRecord,
    AlertUpdate,
    AppStore,
    AssessmentRecord,
    CaseActionCreate,
    CaseActionRecord,
    CheckinCreate,
    CheckinRecord,
    DemoUser,
    MetricSnapshot,
    YouthDetail,
    YouthListItem,
)
from app.services.metrics_service import calculate_metrics
from app.services.seed_service import build_store_from_personas


KST = timezone(timedelta(hours=9), name="KST")


class ApplicationService:
    def __init__(
        self,
        repository: DataRepository,
        coordinator: AnalysisCoordinator,
        personas_path: Path,
    ):
        self.repository = repository
        self.coordinator = coordinator
        self.personas_path = personas_path

    async def initialize(self, *, force: bool = False) -> bool:
        seeded = self.repository.initialize(build_store_from_personas(self.personas_path), force=force)
        store = self.repository.load()
        existing = {item.youthId for item in store.assessments}
        for youth in store.youths:
            if force or youth.youthId not in existing:
                await self.analyze_youth(youth.youthId, mode="rule")
        return seeded

    def _get_youth_or_404(self, store: AppStore, youth_id: str):
        youth = next((item for item in store.youths if item.youthId == youth_id), None)
        if youth is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="청년 정보를 찾을 수 없습니다.")
        return youth

    @staticmethod
    def _latest_assessment(store: AppStore, youth_id: str) -> AssessmentRecord | None:
        items = [item for item in store.assessments if item.youthId == youth_id]
        return max(items, key=lambda item: item.createdAt, default=None)

    @staticmethod
    def _latest_metric(store: AppStore, youth_id: str) -> MetricSnapshot | None:
        return next((item for item in store.metrics if item.youthId == youth_id), None)

    def list_youths(self, *, query: str | None = None, label: str | None = None) -> list[YouthListItem]:
        store = self.repository.load()
        query_value = (query or "").strip().lower()
        results: list[YouthListItem] = []
        for youth in store.youths:
            assessment = self._latest_assessment(store, youth.youthId)
            metric = self._latest_metric(store, youth.youthId) or calculate_metrics(youth.youthId, store.checkins)
            current_label = assessment.label if assessment else "정상"
            if label and current_label != label:
                continue
            if query_value and query_value not in youth.name.lower() and query_value not in youth.region.lower():
                continue
            has_alert = any(
                item.youthId == youth.youthId and item.status in {"미확인", "연락필요", "관찰지속"}
                for item in store.alerts
            )
            results.append(
                YouthListItem(
                    youthId=youth.youthId,
                    name=youth.name,
                    age=youth.age,
                    region=youth.region,
                    status=current_label,
                    lastResponseAt=metric.lastResponseAt,
                    responseRate=metric.responseRateOverall,
                    hasAlert=has_alert,
                )
            )
        severity = {"훼손 의심": 0, "관심 필요": 1, "정상": 2}
        return sorted(results, key=lambda item: (severity[item.status], item.name))

    def get_youth_detail(self, youth_id: str) -> YouthDetail:
        store = self.repository.load()
        youth = self._get_youth_or_404(store, youth_id)
        metric = self._latest_metric(store, youth_id) or calculate_metrics(youth_id, store.checkins)
        assessment = self._latest_assessment(store, youth_id)
        if assessment is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="분석 결과가 아직 준비되지 않았습니다.")
        checkins = sorted(
            (item for item in store.checkins if item.youthId == youth_id),
            key=lambda item: (item.date, item.createdAt),
            reverse=True,
        )
        actions = sorted(
            (item for item in store.caseActions if item.youthId == youth_id),
            key=lambda item: item.createdAt,
            reverse=True,
        )
        return YouthDetail(youth=youth, metrics=metric, assessment=assessment, checkins=checkins, caseActions=actions)

    def get_checkins(self, youth_id: str) -> list[CheckinRecord]:
        store = self.repository.load()
        self._get_youth_or_404(store, youth_id)
        return sorted(
            (item for item in store.checkins if item.youthId == youth_id),
            key=lambda item: (item.date, item.createdAt),
            reverse=True,
        )

    async def create_checkin(self, request: CheckinCreate) -> tuple[CheckinRecord, AssessmentRecord]:
        store = self.repository.load()
        self._get_youth_or_404(store, request.youthId)
        now = datetime.now(KST)
        checkin_date = request.date or now.date()
        record = CheckinRecord(
            checkinId=str(uuid4()),
            youthId=request.youthId,
            date=checkin_date,
            sent=True,
            message="오늘 하루는 어떠셨나요?",
            responded=True,
            responseTimeMinutes=request.responseTimeMinutes,
            responseType=request.responseType,
            responseText=request.responseText,
            followUps=request.followUps,
            createdAt=now,
        )

        def mutate(current: AppStore) -> None:
            # 하루 한 번 응답: 같은 날짜의 기존 응답은 최신 제출로 교체한다.
            current.checkins = [
                item for item in current.checkins if not (item.youthId == request.youthId and item.date == checkin_date)
            ]
            current.checkins.append(record)

        self.repository.transaction(mutate)
        assessment = await self.analyze_youth(request.youthId)
        return record, assessment

    async def analyze_youth(self, youth_id: str, *, mode: str | None = None) -> AssessmentRecord:
        store = self.repository.load()
        self._get_youth_or_404(store, youth_id)
        youth_checkins = [item for item in store.checkins if item.youthId == youth_id]
        metrics = calculate_metrics(youth_id, youth_checkins)
        coordinated = await self.coordinator.run(metrics, youth_checkins, mode=mode)
        now = datetime.now(KST)
        assessment = AssessmentRecord(
            assessmentId=str(uuid4()),
            youthId=youth_id,
            label=coordinated.output.label,
            summary=coordinated.output.summary,
            evidence=coordinated.output.evidence,
            analyzer=coordinated.analyzer,
            analyzerVersion=coordinated.analyzer_version,
            promptVersion=coordinated.prompt_version,
            needsReview=coordinated.output.needsReview,
            disagreement=coordinated.disagreement,
            ruleLabel=coordinated.rule_label,
            aiLabel=coordinated.ai_label,
            createdAt=now,
        )

        def mutate(current: AppStore) -> None:
            current.metrics = [item for item in current.metrics if item.youthId != youth_id]
            current.metrics.append(metrics)
            current.assessments.append(assessment)
            if assessment.label == "정상":
                return

            open_alert = next(
                (
                    item
                    for item in current.alerts
                    if item.youthId == youth_id and item.status in {"미확인", "관찰지속"}
                ),
                None,
            )
            if open_alert:
                open_alert.assessmentId = assessment.assessmentId
                open_alert.label = assessment.label
                open_alert.summary = assessment.summary
                open_alert.evidence = assessment.evidence
                open_alert.updatedAt = now
            else:
                current.alerts.append(
                    AlertRecord(
                        alertId=str(uuid4()),
                        youthId=youth_id,
                        assessmentId=assessment.assessmentId,
                        label=assessment.label,
                        summary=assessment.summary,
                        evidence=assessment.evidence,
                        status="미확인",
                        createdAt=now,
                        updatedAt=now,
                    )
                )

        self.repository.transaction(mutate)
        return assessment

    def list_alerts(self) -> list[AlertRecord]:
        store = self.repository.load()
        return sorted(store.alerts, key=lambda item: item.updatedAt, reverse=True)

    def update_alert(self, alert_id: str, request: AlertUpdate) -> AlertRecord:
        result: AlertRecord | None = None

        def mutate(store: AppStore) -> None:
            nonlocal result
            alert = next((item for item in store.alerts if item.alertId == alert_id), None)
            if alert is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림을 찾을 수 없습니다.")
            alert.status = request.status
            alert.updatedAt = datetime.now(KST)
            result = alert.model_copy(deep=True)

        self.repository.transaction(mutate)
        assert result is not None
        return result

    def get_actions(self, youth_id: str) -> list[CaseActionRecord]:
        store = self.repository.load()
        self._get_youth_or_404(store, youth_id)
        return sorted(
            (item for item in store.caseActions if item.youthId == youth_id),
            key=lambda item: item.createdAt,
            reverse=True,
        )

    def create_action(self, youth_id: str, request: CaseActionCreate, user: DemoUser) -> CaseActionRecord:
        store = self.repository.load()
        self._get_youth_or_404(store, youth_id)
        record = CaseActionRecord(
            actionId=str(uuid4()),
            youthId=youth_id,
            status=request.status,
            memo=request.memo,
            caseWorker=user.name,
            createdAt=datetime.now(KST),
        )

        def mutate(current: AppStore) -> None:
            current.caseActions.append(record)
            for alert in current.alerts:
                if alert.youthId == youth_id and alert.status in {"미확인", "연락필요", "관찰지속"}:
                    alert.status = request.status
                    alert.updatedAt = record.createdAt

        self.repository.transaction(mutate)
        return record
