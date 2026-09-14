from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean

from app.schemas.models import CheckinRecord, MetricSnapshot


KST = timezone(timedelta(hours=9), name="KST")
MOOD_SCORES = {
    "좋음": 4,
    "좋아요": 4,
    "보통": 3,
    "그냥 그래요": 3,
    "힘듦": 2,
    "좀 힘들어요": 2,
    "매우 힘듦": 1,
    "많이 힘들어요": 1,
}


def _rate(items: list[CheckinRecord]) -> float:
    sent = [item for item in items if item.sent]
    if not sent:
        return 0.0
    return round(sum(1 for item in sent if item.responded) / len(sent) * 100, 1)


def _average_response_time(items: list[CheckinRecord]) -> float | None:
    values = [item.responseTimeMinutes for item in items if item.responded and item.responseTimeMinutes is not None]
    return round(mean(values), 1) if values else None


def _average_mood(items: list[CheckinRecord]) -> float | None:
    values = [MOOD_SCORES[item.responseType] for item in items if item.responded and item.responseType in MOOD_SCORES]
    return round(mean(values), 2) if values else None


def calculate_metrics(youth_id: str, checkins: list[CheckinRecord]) -> MetricSnapshot:
    records = sorted((item for item in checkins if item.youthId == youth_id), key=lambda item: (item.date, item.createdAt))
    sent_records = [item for item in records if item.sent]
    now = datetime.now(KST)

    if not sent_records:
        return MetricSnapshot(youthId=youth_id, updatedAt=now)

    latest_date = sent_records[-1].date
    recent_start = latest_date - timedelta(days=6)
    previous_start = latest_date - timedelta(days=13)
    previous_end = latest_date - timedelta(days=7)
    recent = [item for item in sent_records if recent_start <= item.date <= latest_date]
    previous = [item for item in sent_records if previous_start <= item.date <= previous_end]

    max_gap = 0
    running_gap = 0
    for item in sent_records:
        if item.responded:
            running_gap = 0
        else:
            running_gap += 1
            max_gap = max(max_gap, running_gap)

    current_gap = 0
    for item in reversed(sent_records):
        if item.responded:
            break
        current_gap += 1

    overall_time = _average_response_time(sent_records)
    recent_time = _average_response_time(recent)
    previous_time = _average_response_time(previous)
    recent_mood = _average_mood(recent)
    previous_mood = _average_mood(previous)

    return MetricSnapshot(
        youthId=youth_id,
        periodStart=sent_records[0].date,
        periodEnd=latest_date,
        sentCount=len(sent_records),
        responseCount=sum(1 for item in sent_records if item.responded),
        responseRateOverall=_rate(sent_records),
        responseRateLast7d=_rate(recent),
        responseRatePrev7d=_rate(previous),
        responseRateChange7d=round(_rate(recent) - _rate(previous), 1),
        maxConsecutiveNoResponse=max_gap,
        currentConsecutiveNoResponse=current_gap,
        averageResponseTimeMinutes=overall_time,
        averageResponseTimeLast7d=recent_time,
        averageResponseTimePrev7d=previous_time,
        responseTimeChangeMinutes=(round(recent_time - previous_time, 1) if recent_time is not None and previous_time is not None else None),
        recentMoodAverage=recent_mood,
        previousMoodAverage=previous_mood,
        moodChange=(round(recent_mood - previous_mood, 2) if recent_mood is not None and previous_mood is not None else None),
        lastResponseAt=max((item.date for item in sent_records if item.responded), default=None),
        updatedAt=now,
    )
