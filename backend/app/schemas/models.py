from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StatusLabel = Literal["정상", "관심 필요", "훼손 의심"]
ActionStatus = Literal["확인완료", "연락필요", "관찰지속"]
AnalyzerName = Literal["rule", "ai", "hybrid", "rule-fallback"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IndependenceStatus(StrictModel):
    careExitDate: Date
    housing: str
    employmentEducation: str


class YouthRecord(StrictModel):
    youthId: str
    name: str
    age: int
    caseWorker: str
    region: str
    scenarioType: str
    scenarioNote: str | None = None
    completeSilence: bool = False
    backstory: str
    independenceStatus: IndependenceStatus


class CheckinRecord(StrictModel):
    checkinId: str
    youthId: str
    date: Date
    sent: bool = True
    message: str | None = None
    responded: bool
    responseTimeMinutes: int | None = Field(default=None, ge=0)
    responseType: str | None = None
    responseText: str | None = None
    followUps: list[str] = Field(default_factory=list)
    createdAt: datetime


class MetricSnapshot(StrictModel):
    youthId: str
    periodStart: Date | None = None
    periodEnd: Date | None = None
    sentCount: int = 0
    responseCount: int = 0
    responseRateOverall: float = 0
    responseRateLast7d: float = 0
    responseRatePrev7d: float = 0
    responseRateChange7d: float = 0
    maxConsecutiveNoResponse: int = 0
    currentConsecutiveNoResponse: int = 0
    averageResponseTimeMinutes: float | None = None
    averageResponseTimeLast7d: float | None = None
    averageResponseTimePrev7d: float | None = None
    responseTimeChangeMinutes: float | None = None
    recentMoodAverage: float | None = None
    previousMoodAverage: float | None = None
    moodChange: float | None = None
    lastResponseAt: Date | None = None
    updatedAt: datetime


class EvidenceItem(StrictModel):
    metric: str
    description: str
    value: float | int | str | None = None
    previousValue: float | int | str | None = None


class AssessmentRecord(StrictModel):
    assessmentId: str
    youthId: str
    label: StatusLabel
    summary: str
    evidence: list[EvidenceItem]
    analyzer: AnalyzerName
    analyzerVersion: str
    promptVersion: str
    needsReview: bool
    disagreement: bool = False
    ruleLabel: StatusLabel | None = None
    aiLabel: StatusLabel | None = None
    createdAt: datetime


class AlertRecord(StrictModel):
    alertId: str
    youthId: str
    assessmentId: str
    label: StatusLabel
    summary: str
    evidence: list[EvidenceItem]
    status: str = "미확인"
    createdAt: datetime
    updatedAt: datetime


class CaseActionRecord(StrictModel):
    actionId: str
    youthId: str
    status: ActionStatus
    memo: str
    caseWorker: str
    createdAt: datetime


class AppStore(StrictModel):
    schemaVersion: int = 1
    youths: list[YouthRecord] = Field(default_factory=list)
    checkins: list[CheckinRecord] = Field(default_factory=list)
    metrics: list[MetricSnapshot] = Field(default_factory=list)
    assessments: list[AssessmentRecord] = Field(default_factory=list)
    alerts: list[AlertRecord] = Field(default_factory=list)
    caseActions: list[CaseActionRecord] = Field(default_factory=list)


class DemoUser(StrictModel):
    userId: str
    name: str
    role: Literal["case_worker", "youth"]
    region: str
    youthId: str | None = None


class LoginRequest(StrictModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    role: Literal["case_worker", "youth"] = "case_worker"


class LoginResponse(StrictModel):
    accessToken: str
    tokenType: Literal["bearer"] = "bearer"
    user: DemoUser
    demoMode: bool = True


class CheckinCreate(StrictModel):
    youthId: str
    date: Date | None = None
    responseType: str = Field(min_length=1)
    responseText: str | None = Field(default=None, max_length=1000)
    followUps: list[str] = Field(default_factory=list)
    responseTimeMinutes: int = Field(default=0, ge=0)


class AlertUpdate(StrictModel):
    status: Literal["미확인", "확인완료", "연락필요", "관찰지속"]


class CaseActionCreate(StrictModel):
    status: ActionStatus
    memo: str = Field(default="", max_length=2000)


class AnalysisRequest(StrictModel):
    mode: Literal["rule", "ai", "hybrid"] | None = None


class YouthListItem(StrictModel):
    youthId: str
    name: str
    age: int
    region: str
    status: StatusLabel
    lastResponseAt: Date | None
    responseRate: float
    hasAlert: bool


class YouthDetail(StrictModel):
    youth: YouthRecord
    metrics: MetricSnapshot
    assessment: AssessmentRecord
    checkins: list[CheckinRecord]
    caseActions: list[CaseActionRecord]
