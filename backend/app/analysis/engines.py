from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.models import CheckinRecord, EvidenceItem, MetricSnapshot, StatusLabel


SEVERITY: dict[StatusLabel, int] = {"정상": 0, "관심 필요": 1, "훼손 의심": 2}


class AnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: StatusLabel
    summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    needsReview: bool = False


class AssessmentEngine(Protocol):
    async def analyze(self, metrics: MetricSnapshot, checkins: list[CheckinRecord]) -> AnalysisOutput:
        ...


class RuleAssessmentEngine:
    def __init__(self, rules_path: Path):
        self.rules_path = rules_path
        self.rules = json.loads(rules_path.read_text(encoding="utf-8"))
        self.version = str(self.rules.get("version", "1"))

    async def analyze(self, metrics: MetricSnapshot, checkins: list[CheckinRecord]) -> AnalysisOutput:
        warning = self.rules["warning"]
        alert = self.rules["alert"]
        evidence: list[EvidenceItem] = []

        is_alert = (
            metrics.responseRateLast7d <= alert["maxRecentResponseRate"]
            or metrics.currentConsecutiveNoResponse >= alert["minConsecutiveNoResponse"]
            or metrics.responseRateChange7d <= -alert["minResponseRateDrop"]
        )
        is_warning = (
            metrics.responseRateLast7d <= warning["maxRecentResponseRate"]
            or metrics.currentConsecutiveNoResponse >= warning["minConsecutiveNoResponse"]
            or metrics.responseRateChange7d <= -warning["minResponseRateDrop"]
            or (metrics.moodChange is not None and metrics.moodChange <= warning["maxMoodChange"])
        )

        if metrics.responseRateChange7d < 0:
            evidence.append(
                EvidenceItem(
                    metric="response_rate_7d",
                    description=f"최근 7일 응답률이 {metrics.responseRatePrev7d:.0f}%에서 {metrics.responseRateLast7d:.0f}%로 감소했습니다.",
                    value=metrics.responseRateLast7d,
                    previousValue=metrics.responseRatePrev7d,
                )
            )
        if metrics.currentConsecutiveNoResponse > 0:
            evidence.append(
                EvidenceItem(
                    metric="consecutive_no_response",
                    description=f"현재 {metrics.currentConsecutiveNoResponse}일 연속 응답이 없습니다.",
                    value=metrics.currentConsecutiveNoResponse,
                )
            )
        if metrics.moodChange is not None and metrics.moodChange < 0:
            evidence.append(
                EvidenceItem(
                    metric="mood_change",
                    description="최근 기분 응답이 직전 기간보다 낮아졌습니다.",
                    value=metrics.recentMoodAverage,
                    previousValue=metrics.previousMoodAverage,
                )
            )

        if is_alert:
            label: StatusLabel = "훼손 의심"
            summary = "응답 단절 또는 큰 폭의 변화가 감지되어 전담요원의 우선 확인이 필요합니다."
        elif is_warning:
            label = "관심 필요"
            summary = "최근 응답 패턴에 변화가 있어 전담요원의 확인이 필요합니다."
        else:
            label = "정상"
            summary = "최근 응답 패턴에서 뚜렷한 지원 공백 신호가 확인되지 않았습니다."

        if not evidence:
            evidence.append(
                EvidenceItem(
                    metric="response_rate_7d",
                    description=f"최근 7일 응답률은 {metrics.responseRateLast7d:.0f}%입니다.",
                    value=metrics.responseRateLast7d,
                )
            )
        return AnalysisOutput(label=label, summary=summary, evidence=evidence, needsReview=label != "정상")


class OpenAIAssessmentEngine:
    prompt_version = "1"

    def __init__(self, *, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def analyze(self, metrics: MetricSnapshot, checkins: list[CheckinRecord]) -> AnalysisOutput:
        recent = sorted(checkins, key=lambda item: item.date)[-14:]
        payload = {
            "model": self.model,
            "store": False,
            "instructions": (
                "당신은 자립준비청년의 응답 패턴 변화를 요약하는 보조 분석기입니다. "
                "의료적 진단이나 확정적 위기 판정을 하지 말고, 정상/관심 필요/훼손 의심 중 하나와 "
                "전담요원이 확인할 정량적 근거만 반환하세요."
            ),
            "input": json.dumps(
                {
                    "metrics": metrics.model_dump(mode="json"),
                    "recentCheckins": [
                        {
                            "date": item.date.isoformat(),
                            "responded": item.responded,
                            "responseType": item.responseType,
                            "responseText": item.responseText,
                            "responseTimeMinutes": item.responseTimeMinutes,
                        }
                        for item in recent
                    ],
                },
                ensure_ascii=False,
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "safety_net_assessment",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {"type": "string", "enum": ["정상", "관심 필요", "훼손 의심"]},
                            "summary": {"type": "string"},
                            "evidence": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "metric": {"type": "string"},
                                        "description": {"type": "string"},
                                        "value": {"type": ["number", "string", "null"]},
                                        "previousValue": {"type": ["number", "string", "null"]},
                                    },
                                    "required": ["metric", "description", "value", "previousValue"],
                                },
                            },
                            "needsReview": {"type": "boolean"},
                        },
                        "required": ["label", "summary", "evidence", "needsReview"],
                    },
                }
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        output_text = body.get("output_text")
        if not output_text:
            for item in body.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        output_text = content.get("text")
                        break
                if output_text:
                    break
        if not output_text:
            raise ValueError("AI 응답에 output_text가 없습니다.")
        return AnalysisOutput.model_validate_json(output_text)


@dataclass
class CoordinatedResult:
    output: AnalysisOutput
    analyzer: str
    rule_label: StatusLabel
    ai_label: StatusLabel | None
    disagreement: bool
    analyzer_version: str
    prompt_version: str


class AnalysisCoordinator:
    def __init__(self, rule_engine: RuleAssessmentEngine):
        self.rule_engine = rule_engine

    async def run(
        self,
        metrics: MetricSnapshot,
        checkins: list[CheckinRecord],
        *,
        mode: str | None = None,
    ) -> CoordinatedResult:
        selected_mode = (mode or os.getenv("ANALYSIS_MODE", "hybrid")).lower()
        if selected_mode not in {"rule", "ai", "hybrid"}:
            selected_mode = "hybrid"

        rule_output = await self.rule_engine.analyze(metrics, checkins)
        if selected_mode == "rule":
            return CoordinatedResult(
                output=rule_output,
                analyzer="rule",
                rule_label=rule_output.label,
                ai_label=None,
                disagreement=False,
                analyzer_version=self.rule_engine.version,
                prompt_version="none",
            )

        api_key = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
        model = os.getenv("AI_MODEL")
        if not api_key or not model:
            return CoordinatedResult(
                output=rule_output,
                analyzer="rule-fallback",
                rule_label=rule_output.label,
                ai_label=None,
                disagreement=False,
                analyzer_version=self.rule_engine.version,
                prompt_version="none",
            )

        try:
            ai_engine = OpenAIAssessmentEngine(api_key=api_key, model=model)
            ai_output = await ai_engine.analyze(metrics, checkins)
        except Exception:
            return CoordinatedResult(
                output=rule_output,
                analyzer="rule-fallback",
                rule_label=rule_output.label,
                ai_label=None,
                disagreement=False,
                analyzer_version=self.rule_engine.version,
                prompt_version="none",
            )

        disagreement = ai_output.label != rule_output.label
        if selected_mode == "ai":
            output = ai_output
            analyzer = "ai"
        else:
            output = ai_output if SEVERITY[ai_output.label] >= SEVERITY[rule_output.label] else rule_output
            output = output.model_copy(update={"needsReview": output.needsReview or disagreement})
            analyzer = "hybrid"

        return CoordinatedResult(
            output=output,
            analyzer=analyzer,
            rule_label=rule_output.label,
            ai_label=ai_output.label,
            disagreement=disagreement,
            analyzer_version=self.rule_engine.version,
            prompt_version=OpenAIAssessmentEngine.prompt_version,
        )

