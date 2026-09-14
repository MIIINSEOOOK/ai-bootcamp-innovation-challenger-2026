from __future__ import annotations

import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.models import DemoUser, LoginRequest, LoginResponse


DEMO_WORKER = DemoUser(
    userId="worker-001",
    name="김지연",
    role="case_worker",
    region="서울 마포·은평·서대문 권역",
)
DEMO_YOUTH = DemoUser(
    userId="youth-P02",
    name="이서연",
    role="youth",
    region="서울 은평구",
    youthId="P02",
)
security = HTTPBearer(auto_error=False)


def _demo_token() -> str:
    return os.getenv("DEMO_TOKEN", "demo-local-token")


def login_demo_user(request: LoginRequest) -> LoginResponse:
    # 입력값은 UI 흐름 확인용이며 실제 자격 증명 검증이 아니다.
    user = DEMO_YOUTH if request.role == "youth" else DEMO_WORKER
    return LoginResponse(accessToken=_demo_token(), user=user, demoMode=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> DemoUser:
    # 로컬 데모에서는 헤더가 없어도 고정 사용자를 사용한다. 잘못된 토큰은 명확히 거부한다.
    if credentials is not None and credentials.credentials != _demo_token():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 데모 토큰입니다.")
    return DEMO_WORKER
