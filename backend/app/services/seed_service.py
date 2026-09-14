from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.schemas.models import (
    AppStore,
    CheckinRecord,
    IndependenceStatus,
    YouthRecord,
)


SEOUL_REGIONS = ["서울 마포구", "서울 은평구", "서울 서대문구"]
KST = timezone(timedelta(hours=9), name="KST")


def build_store_from_personas(personas_path: Path) -> AppStore:
    raw_personas = json.loads(personas_path.read_text(encoding="utf-8"))
    youths: list[YouthRecord] = []
    checkins: list[CheckinRecord] = []

    for index, persona in enumerate(raw_personas):
        youth_id = persona["persona_id"]
        independence = persona["independence_status"]
        youths.append(
            YouthRecord(
                youthId=youth_id,
                name=persona["name"],
                age=persona["age"],
                caseWorker=persona["case_worker"],
                region=SEOUL_REGIONS[index % len(SEOUL_REGIONS)],
                scenarioType=persona["scenario_type"],
                scenarioNote=persona.get("scenario_note"),
                completeSilence=persona.get("complete_silence", False),
                backstory=persona["backstory"],
                independenceStatus=IndependenceStatus(
                    careExitDate=independence["care_exit_date"],
                    housing=independence["housing"],
                    employmentEducation=independence["employment_education"],
                ),
            )
        )

        for log_index, log in enumerate(persona["daily_logs"]):
            log_date = log["date"]
            checkins.append(
                CheckinRecord(
                    checkinId=f"{youth_id}-{log_date}-{log_index}",
                    youthId=youth_id,
                    date=log_date,
                    sent=log["sent"],
                    message=log.get("message"),
                    responded=log["responded"],
                    responseTimeMinutes=log.get("response_time_minutes"),
                    responseType=log.get("response_type"),
                    responseText=log.get("response_text"),
                    followUps=log.get("follow_ups", []),
                    createdAt=datetime.fromisoformat(f"{log_date}T09:00:00").replace(tzinfo=KST),
                )
            )

    return AppStore(schemaVersion=1, youths=youths, checkins=checkins)
