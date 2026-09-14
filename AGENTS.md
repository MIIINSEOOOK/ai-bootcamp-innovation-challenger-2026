# Project Context: 자립동행 MVP

이 파일은 새 Codex 세션이 프로젝트 맥락과 사용자의 결정을 자동으로 이어받기 위한 저장소 루트 지침이다. 작업을 시작할 때 이 파일과 `docs/기능명세서.md`, `docs/시스템동작설명서.md`, `docs/프로젝트인수인계.md`를 먼저 확인한다.

## Product goal

자립준비청년의 일상 안부 응답을 축적하고 응답 패턴 변화를 분석하여, 지원 공백 가능성을 전담요원에게 근거와 함께 보여주는 로컬 시연용 웹 MVP다. 의료 진단이나 확정 위험등급을 만드는 서비스가 아니다. 실제 판단과 개입은 전담요원이 수행한다.

구현 범위는 기능명세서의 F1~F7이다. F8 사례관리 문서 자동화, F9 지원제도 매칭, 운영 배포, 외부 메시지 연동은 사용자가 별도로 요청하기 전까지 추가하지 않는다.

## User decisions that must be preserved

- 로컬 시연 기준이다.
- 프런트엔드 하드코딩 대신 실제 FastAPI 서버가 동작해야 한다.
- 운영 DB는 아직 사용하지 않고 서버 측 JSON으로 데이터를 관리한다.
- 브라우저 `localStorage`는 업무 데이터의 주 저장소로 사용하지 않는다.
- 인증은 데모 구현이지만 나중에 외부 인증 공급자로 교체 가능한 경계를 유지한다.
- 분석은 `rule`, `ai`, `hybrid` 모드를 지원하고 AI 키나 호출에 문제가 있으면 규칙 분석으로 폴백한다.
- AI 키는 백엔드 환경변수에서만 읽는다.
- Figma Make 화면은 색상·시각 언어의 참고 자료다. 화면 전환용 상단 데모 바는 실제 서비스에 맞지 않아 제거했다. 다시 추가하지 않는다.
- 참고 Figma Make: `https://www.figma.com/make/v9dwYzJTQClOwGfIvY9dc5/Social-Impact-Service-UI-UX--%EB%B3%B5%EC%82%AC-`
- 실제 사용자 흐름은 `청년 로그인 → 안부 설문 → 완료`, `전담요원 로그인 → 담당 청년/알림 → 상세·조치`다.
- 실행 진입점은 Python `manage.py`다. BAT 파일은 Python을 호출한다. PowerShell 스크립트는 삭제했으므로 다시 만들지 않는다.
- Git 커밋, 푸시, 배포는 사용자가 명시적으로 요청할 때만 한다.

## Current implementation

### Frontend

- 위치: `Social Impact Service UI_UX (복사)`
- React 19, TypeScript, Vite, Tailwind CSS 4, Recharts
- 기본 포트: 8443
- `/api`는 Vite proxy를 통해 `http://127.0.0.1:8000`으로 전달한다.
- 시작 화면은 청년/전담요원 역할 선택 로그인이다.
- 청년 데모 계정은 API가 반환하는 `youthId=P02`, 이름 `이서연`과 연결된다.
- 전담요원 화면에는 공통 서비스 헤더, 담당 청년 메뉴, 알림 센터, 사용자 정보, 로그아웃이 있다.
- API 경계: `src/lib/api.ts`
- 서버 응답 타입: `src/types.ts`

### Backend

- 위치: `backend`
- FastAPI, Pydantic, Uvicorn
- 기본 포트: 8000
- 앱 진입점: `backend/app/main.py`
- API 라우트: `backend/app/api/routes.py`
- 인증 교체 지점: `backend/app/auth/demo.py`
- 업무 흐름: `backend/app/services/application_service.py`
- 지표 계산: `backend/app/services/metrics_service.py`
- 분석 엔진: `backend/app/analysis/engines.py`
- 저장소 인터페이스: `backend/app/repositories/base.py`
- JSON 구현: `backend/app/repositories/json_repository.py`

### Data

- 시드: `data/personas/personas.json` — 12명, 60일씩 총 720개 안부 로그
- 런타임 저장소: `backend/data/app_data.json`
- 백업: `backend/data/app_data.json.bak`
- 분석 기준: `backend/config/analysis_rules.json`
- 런타임 JSON은 Git ignore 대상이다.
- `data/jaripon`은 현재 F1~F7 런타임에서 사용하지 않는 F9 후보 데이터다. 사용자 승인 없이 삭제하거나 기능에 연결하지 않는다.

JSON 저장은 Pydantic 전체 검증, 프로세스 내부 잠금, 같은 폴더의 임시 파일 기록, `os.replace` 원자 교체, 기존 파일 백업 순서로 수행한다. 이 저장 방식은 단일 로컬 서버 프로세스 전용이다.

## Demo accounts

- 청년: `lee.seoyeon` / `demo`
- 전담요원: `kim.jiyeon` / `demo`

현재 데모 로그인은 비어 있지 않은 입력과 선택 역할을 받아 고정 사용자를 반환한다. 실제 자격 증명 검증으로 오해하지 않는다.

## Commands

저장소 루트에서 실행한다.

```bat
scripts\dev.bat
scripts\reset-demo.bat
scripts\smoke-test.bat
```

Python 직접 실행:

```powershell
.\.venv\Scripts\python.exe .\manage.py dev
.\.venv\Scripts\python.exe .\manage.py reset
.\.venv\Scripts\python.exe .\manage.py smoke
```

웹: `http://127.0.0.1:8443`

API 문서: `http://127.0.0.1:8000/docs`

`manage.py dev`는 백엔드 health check 후 Vite를 시작하고 종료 시 자신이 시작한 프로세스 트리를 정리한다.

## Verification

백엔드:

```powershell
Push-Location .\backend
..\.venv\Scripts\python.exe -m pytest
Pop-Location
```

프런트엔드:

```powershell
Push-Location '.\Social Impact Service UI_UX (복사)'
npx.cmd tsc --noEmit
npm.cmd run build
Pop-Location
```

마지막 확인 상태는 백엔드 테스트 10개 통과, TypeScript 검사 통과, Vite 프로덕션 빌드 통과다. 스모크 테스트는 런타임 데이터를 변경하므로 완료 후 `manage.py reset`을 실행한다.

## Working rules for future sessions

- 변경 전에 `git status --short`를 확인하고 사용자 변경을 보존한다.
- 동작을 바꾸면 README와 `docs/시스템동작설명서.md`도 함께 갱신한다.
- 현재 디자인 토큰과 시각 언어는 유지하되, Figma의 화면 전환 데모 구조를 그대로 복원하지 않는다.
- 목록·알림·상세·응답의 주요 데이터는 API에서 가져온다. 새 하드코딩 업무 데이터를 화면에 추가하지 않는다.
- Repository와 인증 의존성 경계를 우회하지 않는다. DB나 외부 인증으로 확장할 때 기존 경계의 구현체를 교체한다.
- API 키, 토큰, 실제 개인정보를 저장소에 기록하지 않는다.
- 테스트 실패를 환경 문제로 단정하기 전에 작업공간 안의 임시 경로와 실제 코드 오류를 구분한다.
- 파괴적 초기화인 `manage.py reset`은 런타임 데모 데이터를 시드로 되돌린다는 점을 사용자에게 알린다.
- 기존 Vite의 미래 호환성 및 번들 크기 경고와 TestClient 의존성 폐기 예정 경고는 비차단 경고다. 관련 패키지를 바꿀 때 다시 평가한다.
