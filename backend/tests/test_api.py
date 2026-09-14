from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import PROJECT_ROOT, create_app
from app.schemas.models import AppStore


def test_health_and_demo_login(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok", "storage": "json", "demoMode": True}
    login = client.post("/api/auth/login", json={"username": "demo", "password": "demo"})
    assert login.status_code == 200
    assert login.json()["demoMode"] is True
    token = login.json()["accessToken"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "case_worker"
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer wrong"}).status_code == 401

    youth_login = client.post(
        "/api/auth/login",
        json={"username": "lee.seoyeon", "password": "demo", "role": "youth"},
    )
    assert youth_login.status_code == 200
    assert youth_login.json()["user"]["role"] == "youth"
    assert youth_login.json()["user"]["youthId"] == "P02"


def test_seed_list_detail_search_and_filter(client: TestClient, data_path: Path) -> None:
    assert data_path.exists()
    store = AppStore.model_validate_json(data_path.read_text(encoding="utf-8"))
    assert len(store.youths) == 12
    assert {youth.caseWorker for youth in store.youths} == {"김지연"}
    assert len(store.checkins) == 720
    assert len(store.metrics) == 12
    assert len(store.assessments) == 12

    youths = client.get("/api/youths")
    assert youths.status_code == 200
    assert len(youths.json()) == 12
    first = youths.json()[0]
    detail = client.get(f"/api/youths/{first['youthId']}")
    assert detail.status_code == 200
    assert detail.json()["youth"]["youthId"] == first["youthId"]
    assert detail.json()["metrics"]["sentCount"] > 0
    seoyeon = client.get("/api/youths/P02").json()
    assert seoyeon["checkins"][0]["followUps"]
    analysis = client.post(f"/api/youths/{first['youthId']}/analysis/current")
    assert analysis.status_code == 200
    assert analysis.json()["analyzer"] == "rule"

    searched = client.get("/api/youths", params={"query": first["name"]})
    assert len(searched.json()) == 1
    filtered = client.get("/api/youths", params={"status": "훼손 의심"})
    assert filtered.status_code == 200
    assert filtered.json()
    assert all(item["status"] == "훼손 의심" for item in filtered.json())


def test_checkin_persists_and_recalculates(client: TestClient, data_path: Path) -> None:
    response = client.post(
        "/api/checkins",
        json={
            "youthId": "P02",
            "date": "2026-09-14",
            "responseType": "좋아요",
            "responseText": "오늘은 조금 편안해요.",
            "followUps": ["밥은 잘 챙겨 먹고 있어요"],
            "responseTimeMinutes": 8,
        },
    )
    assert response.status_code == 200
    assert response.json()["checkin"]["responseText"] == "오늘은 조금 편안해요."
    assert response.json()["checkin"]["followUps"] == ["밥은 잘 챙겨 먹고 있어요"]

    detail = client.get("/api/youths/P02").json()
    assert detail["checkins"][0]["date"] == "2026-09-14"
    assert detail["metrics"]["periodEnd"] == "2026-09-14"

    restarted_app = create_app(
        data_path=data_path,
        personas_path=PROJECT_ROOT / "data" / "personas" / "personas.json",
    )
    with TestClient(restarted_app) as restarted:
        persisted = restarted.get("/api/youths/P02").json()
        assert persisted["checkins"][0]["responseText"] == "오늘은 조금 편안해요."


def test_analysis_alert_and_case_action_flow(client: TestClient) -> None:
    assessment = client.post("/api/youths/P10/analyze", json={"mode": "rule"})
    assert assessment.status_code == 200
    assert assessment.json()["label"] == "훼손 의심"
    assert assessment.json()["evidence"]

    alerts = client.get("/api/alerts")
    assert alerts.status_code == 200
    youth_alert = next(item for item in alerts.json() if item["youthId"] == "P10")
    updated = client.patch(f"/api/alerts/{youth_alert['alertId']}", json={"status": "관찰지속"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "관찰지속"

    action = client.post(
        "/api/youths/P10/actions",
        json={"status": "연락필요", "memo": "오후에 연락을 시도하기로 함"},
    )
    assert action.status_code == 200
    actions = client.get("/api/youths/P10/actions").json()
    assert actions[0]["memo"] == "오후에 연락을 시도하기로 함"
    refreshed_alert = next(item for item in client.get("/api/alerts").json() if item["youthId"] == "P10")
    assert refreshed_alert["status"] == "연락필요"


def test_ai_mode_without_key_uses_rule_fallback(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = client.post("/api/youths/P05/analyze", json={"mode": "ai"})
    assert result.status_code == 200
    assert result.json()["analyzer"] == "rule-fallback"


def test_ai_failure_uses_rule_fallback(client: TestClient, monkeypatch) -> None:
    from app.analysis.engines import OpenAIAssessmentEngine

    async def fail(*_args, **_kwargs):
        raise RuntimeError("simulated provider failure")

    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setattr(OpenAIAssessmentEngine, "analyze", fail)
    result = client.post("/api/youths/P05/analyze", json={"mode": "hybrid"})
    assert result.status_code == 200
    assert result.json()["analyzer"] == "rule-fallback"


def test_invalid_requests_are_rejected(client: TestClient) -> None:
    assert client.post("/api/checkins", json={"youthId": "P01"}).status_code == 422
    assert client.post(
        "/api/checkins",
        json={"youthId": "missing", "responseType": "보통"},
    ).status_code == 404
    assert client.patch("/api/alerts/missing", json={"status": "확인완료"}).status_code == 404
    assert client.get("/api/youths/missing").status_code == 404
