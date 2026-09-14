from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.schemas.models import CheckinRecord
from app.services.metrics_service import calculate_metrics


KST = timezone(timedelta(hours=9))


def make_checkin(day: int, responded: bool, response_type: str | None = "보통") -> CheckinRecord:
    value = date(2026, 9, day)
    return CheckinRecord(
        checkinId=f"c-{day}",
        youthId="P99",
        date=value,
        sent=True,
        responded=responded,
        responseTimeMinutes=10 if responded else None,
        responseType=response_type if responded else None,
        createdAt=datetime(2026, 9, day, 9, tzinfo=KST),
    )


def test_metrics_are_calculated_from_raw_checkins() -> None:
    items = [make_checkin(day, day <= 7) for day in range(1, 15)]
    metrics = calculate_metrics("P99", items)
    assert metrics.responseRatePrev7d == 100
    assert metrics.responseRateLast7d == 0
    assert metrics.responseRateChange7d == -100
    assert metrics.currentConsecutiveNoResponse == 7
    assert metrics.maxConsecutiveNoResponse == 7
    assert metrics.lastResponseAt == date(2026, 9, 7)

