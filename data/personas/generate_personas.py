#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
자립준비청년 안전망 훼손 감지 AI 에이전트 — 데모용 페르소나 생성기

기능명세서(F3) "청년별 시나리오(정상 유지형/점진적 악화형/급격한 단절형 등)
샘플 데이터를 미리 구성해 시연"을 위해, 완전히 가상의 인물 12명과 60일치
안부 응답 로그를 결정론적으로(고정 시드) 생성한다. 실제 청년 개인정보는
전혀 사용하지 않는다.

실행:
    python generate_personas.py
    -> personas.json 저장 (이 스크립트와 같은 디렉토리)
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

PERIOD_DAYS = 60
END_DATE = date(2026, 9, 13)
START_DATE = END_DATE - timedelta(days=PERIOD_DAYS - 1)

MESSAGE_TEMPLATES = [
    "오늘 하루 어떻게 보내고 계세요? 편하게 눌러주세요 🙂",
    "안녕하세요! 오늘 컨디션은 어떠세요?",
    "오늘도 잘 지내고 계신가요? 짧게라도 알려주세요.",
]

POSITIVE_TEXTS = ["네 잘 지내고 있어요!", "오늘도 무난했어요", "별일 없어요~", "좋아요 :)", "그럭저럭 괜찮아요"]
NEUTRAL_TEXTS = ["그냥 그래요", "평범한 하루였어요", "특별한 건 없었어요", "그저 그랬어요"]
NEGATIVE_TEXTS = ["요즘 좀 힘드네요", "생각이 많아지는 요즘이에요", "잠을 잘 못 잤어요", "조금 지쳐요", "일이 잘 안 풀려요"]


def daterange(start: date, days: int):
    for i in range(days):
        yield start + timedelta(days=i)


def pick_response_type(mood_score: float, rng: random.Random) -> str:
    """mood_score 0~1, 높을수록 긍정적인 응답이 나올 확률이 높다."""
    r = rng.random()
    if mood_score >= 0.66:
        return "좋음" if r < 0.75 else "보통"
    if mood_score >= 0.33:
        if r < 0.55:
            return "보통"
        return "좋음" if r < 0.8 else "힘듦"
    return "힘듦" if r < 0.6 else "보통"


def pick_text(response_type: str, rng: random.Random) -> str:
    pool = {"좋음": POSITIVE_TEXTS, "보통": NEUTRAL_TEXTS, "힘듦": NEGATIVE_TEXTS}[response_type]
    return rng.choice(pool)


def make_log(d: date, rng: random.Random, responded: bool, resp_min: int | None,
             rtype: str | None, rtext: str | None) -> dict[str, Any]:
    return {
        "date": d.isoformat(),
        "sent": True,
        "message": rng.choice(MESSAGE_TEMPLATES),
        "responded": responded,
        "response_time_minutes": resp_min,
        "response_type": rtype,
        "response_text": rtext,
    }


def build_logs_stable(rng: random.Random, busy: bool = False) -> list[dict[str, Any]]:
    logs = []
    miss_streak = 0
    base_prob = 0.80 if busy else 0.90
    for d in daterange(START_DATE, PERIOD_DAYS):
        respond_prob = base_prob if miss_streak < 2 else 0.97
        responded = rng.random() < respond_prob
        if responded:
            miss_streak = 0
            resp_min = rng.randint(60, 480) if busy else rng.randint(5, 240)
            rtype = pick_response_type(0.75, rng)
            rtext = pick_text(rtype, rng)
        else:
            miss_streak += 1
            resp_min = rtype = rtext = None
        logs.append(make_log(d, rng, responded, resp_min, rtype, rtext))
    return logs


def build_logs_gradual_decline(rng: random.Random, severity: float = 0.75) -> list[dict[str, Any]]:
    """severity: 기간 종료 시점까지 응답 확률이 얼마나 떨어지는지 (0.9 - severity가 최종 확률)."""
    logs = []
    for i, d in enumerate(daterange(START_DATE, PERIOD_DAYS)):
        progress = i / (PERIOD_DAYS - 1)
        respond_prob = 0.90 - severity * progress
        mood = 0.85 - severity * progress
        responded = rng.random() < respond_prob
        if responded:
            resp_min = max(3, int(20 + 500 * progress) + rng.randint(-15, 60))
            rtype = pick_response_type(mood, rng)
            rtext = pick_text(rtype, rng)
        else:
            resp_min = rtype = rtext = None
        logs.append(make_log(d, rng, responded, resp_min, rtype, rtext))
    return logs


def build_logs_abrupt(rng: random.Random, cutoff_day: int, post_cutoff_prob: float) -> list[dict[str, Any]]:
    logs = []
    for i, d in enumerate(daterange(START_DATE, PERIOD_DAYS)):
        if i < cutoff_day:
            responded = rng.random() < 0.88
            mood = 0.7
        else:
            responded = rng.random() < post_cutoff_prob
            mood = 0.2
        if responded:
            resp_min = rng.randint(10, 180) if i < cutoff_day else rng.randint(300, 900)
            rtype = pick_response_type(mood, rng)
            rtext = pick_text(rtype, rng)
        else:
            resp_min = rtype = rtext = None
        logs.append(make_log(d, rng, responded, resp_min, rtype, rtext))
    return logs


BUILDERS: dict[str, Callable[[random.Random], list[dict[str, Any]]]] = {
    "stable": lambda rng: build_logs_stable(rng, busy=False),
    "stable_busy": lambda rng: build_logs_stable(rng, busy=True),
    "gradual": lambda rng: build_logs_gradual_decline(rng, severity=0.75),
    "gradual_mild": lambda rng: build_logs_gradual_decline(rng, severity=0.40),
    "gradual_moderate": lambda rng: build_logs_gradual_decline(rng, severity=0.58),
    "abrupt_sparse": lambda rng: build_logs_abrupt(rng, cutoff_day=45, post_cutoff_prob=0.12),
    "abrupt_silent": lambda rng: build_logs_abrupt(rng, cutoff_day=42, post_cutoff_prob=0.0),
    "abrupt_recent": lambda rng: build_logs_abrupt(rng, cutoff_day=57, post_cutoff_prob=0.0),
}


def compute_summary(logs: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(logs)
    flags = [bool(l["responded"]) for l in logs]
    overall_rate = sum(flags) / n

    last7 = flags[-7:]
    prev7 = flags[-14:-7] if n >= 14 else last7
    rate_last7 = sum(last7) / len(last7)
    rate_prev7 = sum(prev7) / len(prev7)

    max_streak = 0
    cur_streak = 0
    for flag in flags:
        if not flag:
            cur_streak += 1
            max_streak = max(max_streak, cur_streak)
        else:
            cur_streak = 0

    trailing_streak = 0
    for flag in reversed(flags):
        if not flag:
            trailing_streak += 1
        else:
            break

    return {
        "period_start": logs[0]["date"],
        "period_end": logs[-1]["date"],
        "period_days": n,
        "response_rate_overall": round(overall_rate, 2),
        "response_rate_last_7d": round(rate_last7, 2),
        "response_rate_prev_7d": round(rate_prev7, 2),
        "response_rate_change_7d": round(rate_last7 - rate_prev7, 2),
        "max_consecutive_no_response": max_streak,
        "current_consecutive_no_response": trailing_streak,
    }


def classify_status(summary: dict[str, Any]) -> str:
    """
    F4의 3단계 분류를 흉내낸 참고용 규칙 기반 판정.
    실제 F4 AI 로직을 대체하는 것이 아니라, 이 페르소나 데이터의
    "기대값(ground truth)"을 매겨 데모/검증에 쓰기 위한 것이다.
    """
    trailing = summary["current_consecutive_no_response"]
    rate_last7 = summary["response_rate_last_7d"]
    change = summary["response_rate_change_7d"]

    if trailing >= 5 or (rate_last7 <= 0.35 and change <= -0.3):
        return "훼손 의심"
    if trailing >= 2 or rate_last7 <= 0.65 or change <= -0.15:
        return "관심 필요"
    return "정상"


def build_rationale(summary: dict[str, Any]) -> str:
    rate_prev_pct = round(summary["response_rate_prev_7d"] * 100)
    rate_last_pct = round(summary["response_rate_last_7d"] * 100)
    streak = summary["current_consecutive_no_response"]

    parts = []
    if abs(rate_last_pct - rate_prev_pct) >= 10:
        direction = "감소" if rate_last_pct < rate_prev_pct else "증가"
        parts.append(f"최근 7일 응답률 {rate_prev_pct}%→{rate_last_pct}%로 {direction}")
    else:
        parts.append(f"최근 7일 응답률 {rate_last_pct}%로 유지")
    if streak >= 2:
        parts.append(f"{streak}일 연속 미응답")
    return ", ".join(parts)


PERSONAS: list[dict[str, Any]] = [
    dict(id="P01", name="김도윤", age=22, case_worker="이하늘 주무관",
         housing="자취(월세)", employment="재직중(제조업 생산직)",
         care_exit_date="2023-02-15",
         scenario_type="정상 유지형", scenario_note="안정적으로 자립 생활 유지",
         backstory="보호종료 후 지역 자활센터 연계로 취업에 성공해 1년 넘게 같은 직장에 다니고 있다. "
                    "자취방에서 혼자 지내지만 동료들과의 관계도 원만한 편이다.",
         builder="stable", seed=1),
    dict(id="P02", name="이서연", age=20, case_worker="박준서 주무관",
         housing="자립생활관", employment="재학중(전문대)",
         care_exit_date="2024-08-01",
         scenario_type="정상 유지형", scenario_note="학업과 생활 병행이 안정적",
         backstory="시설 퇴소 후 자립생활관에 입주해 학업을 이어가고 있다. "
                    "또래 자립준비청년들과 함께 지내며 정서적으로도 안정된 편이다.",
         builder="stable", seed=2),
    dict(id="P03", name="박지훈", age=24, case_worker="이하늘 주무관",
         housing="친인척 동거", employment="재직중(계약직 사무보조)",
         care_exit_date="2021-11-20",
         scenario_type="정상 유지형", scenario_note="야근 등으로 응답이 가끔 늦지만 전반적으로 안정",
         backstory="이모 댁에서 지내며 계약직으로 근무 중이다. "
                    "야근이 잦아 응답이 늦어질 때가 있지만 꾸준히 안부를 전한다.",
         builder="stable_busy", seed=3),
    dict(id="P04", name="최하늘", age=19, case_worker="박준서 주무관",
         housing="자립생활관", employment="훈련중(직업훈련원 바리스타 과정)",
         care_exit_date="2025-01-10",
         scenario_type="정상 유지형", scenario_note="밝고 적극적으로 소통하는 편",
         backstory="바리스타 자격증반을 다니며 카페 창업을 꿈꾸고 있다. "
                    "성격이 밝아 안부 메시지에도 적극적으로 응답한다.",
         builder="stable", seed=4),

    dict(id="P05", name="정민준", age=23, case_worker="한소미 주무관",
         housing="자취(월세)", employment="구직중",
         care_exit_date="2022-05-30",
         scenario_type="점진적 악화형", scenario_note="반복된 취업 실패로 서서히 무기력해짐",
         backstory="여러 차례 취업에 실패하며 점점 의욕을 잃어가고 있다. "
                    "처음에는 꼬박꼬박 응답했지만 최근 들어 응답이 뜸해지고 내용도 부정적으로 변하고 있다.",
         builder="gradual", seed=5),
    dict(id="P06", name="한소율", age=21, case_worker="이하늘 주무관",
         housing="자취(전세)", employment="재학중 + 아르바이트",
         care_exit_date="2023-09-01",
         scenario_type="점진적 악화형", scenario_note="학업·알바 병행으로 인한 번아웃",
         backstory="학비와 생활비를 벌기 위해 학업과 아르바이트를 병행하다 서서히 지쳐가고 있다.",
         builder="gradual_mild", seed=6),
    dict(id="P07", name="오지안", age=25, case_worker="한소미 주무관",
         housing="친인척 동거", employment="재직중(콜센터)",
         care_exit_date="2020-12-01",
         scenario_type="점진적 악화형", scenario_note="직장 내 갈등으로 위축",
         backstory="직장에서의 갈등 이후 조금씩 의기소침해지고 있다. "
                    "겉으로는 티를 안 내려 하지만 응답 패턴에 변화가 나타나고 있다.",
         builder="gradual_moderate", seed=7),
    dict(id="P08", name="신다은", age=20, case_worker="박준서 주무관",
         housing="자립생활관", employment="무직",
         care_exit_date="2024-03-15",
         scenario_type="점진적 악화형", scenario_note="장기 구직 실패로 고립 심화",
         backstory="구직 기간이 길어지며 점점 방 밖으로 나가지 않는 날이 늘고 있다.",
         builder="gradual", seed=8),

    dict(id="P09", name="강태오", age=22, case_worker="한소미 주무관",
         housing="자취(월세)", employment="무직(최근 퇴사)",
         care_exit_date="2023-06-10",
         scenario_type="급격한 단절형", scenario_note="갑작스러운 실직 이후 거의 응답 없음",
         backstory="다니던 직장에서 갑자기 퇴사한 이후 연락이 눈에 띄게 줄었다. "
                    "드물게 응답이 오지만 대부분은 침묵이다.",
         builder="abrupt_sparse", seed=9),
    dict(id="P10", name="윤하람", age=24, case_worker="이하늘 주무관",
         housing="자취(월세)", employment="무직",
         care_exit_date="2022-02-20",
         scenario_type="급격한 단절형", scenario_note="완전 무응답형 — 특정 시점 이후 응답 0건",
         backstory="한동안 잘 지내는 듯했으나 최근 몇 주간 단 한 번도 응답이 없다. "
                    "전화도 받지 않아 담당 전담요원이 방문을 고려하고 있다.",
         builder="abrupt_silent", seed=10),
    dict(id="P11", name="조은우", age=19, case_worker="박준서 주무관",
         housing="자립생활관 퇴소 후 미상", employment="재학중",
         care_exit_date="2025-02-01",
         scenario_type="급격한 단절형", scenario_note="완전 무응답형 — 시설 퇴소 후 연락 두절",
         backstory="자립생활관을 나간 이후 새 거주지를 전담요원에게 알리지 않은 채 연락이 완전히 끊겼다.",
         builder="abrupt_silent", seed=11),
    dict(id="P12", name="임소망", age=23, case_worker="한소미 주무관",
         housing="친인척 동거", employment="재직중",
         care_exit_date="2021-08-25",
         scenario_type="급격한 단절형", scenario_note="가족 갈등 이후 최근 며칠간 급격히 응답 중단(초기 포착 사례)",
         backstory="가족과의 갈등 이후 최근 며칠 새 갑자기 응답이 끊겼다. "
                    "아직 기간이 길지는 않아 조기에 포착된 사례다.",
         builder="abrupt_recent", seed=12),
]


def build_persona(spec: dict[str, Any]) -> dict[str, Any]:
    rng = random.Random(spec["seed"])
    logs = BUILDERS[spec["builder"]](rng)
    summary = compute_summary(logs)
    label = classify_status(summary)
    rationale = build_rationale(summary)

    return {
        "persona_id": spec["id"],
        "name": spec["name"],
        "age": spec["age"],
        "case_worker": spec["case_worker"],
        "independence_status": {
            "care_exit_date": spec["care_exit_date"],
            "housing": spec["housing"],
            "employment_education": spec["employment"],
        },
        "scenario_type": spec["scenario_type"],
        "scenario_note": spec["scenario_note"],
        "complete_silence": spec["builder"] == "abrupt_silent",
        "backstory": spec["backstory"],
        "daily_logs": logs,
        "derived_summary": summary,
        "expected_ai_label": label,
        "expected_rationale_example": rationale,
    }


def main() -> None:
    personas = [build_persona(spec) for spec in PERSONAS]
    out_path = Path(__file__).parent / "personas.json"
    out_path.write_text(json.dumps(personas, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[완료] {len(personas)}명 저장 -> {out_path}")
    for p in personas:
        s = p["derived_summary"]
        print(
            f"  {p['persona_id']} {p['name']:4s} {p['scenario_type']:8s} "
            f"label={p['expected_ai_label']:6s} "
            f"overall={s['response_rate_overall']:.2f} last7={s['response_rate_last_7d']:.2f} "
            f"trailing_miss={s['current_consecutive_no_response']}"
        )


if __name__ == "__main__":
    main()
