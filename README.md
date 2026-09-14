# 자립준비청년 안전망 훼손 감지 AI 에이전트

자립준비청년의 일상 응답 패턴 변화를 분석해 지원 공백 가능성을 전담요원에게 근거와 함께 보여주는 로컬 시연용 웹 MVP입니다.

- 기능 범위: [기능명세서](docs/기능명세서.md)
- 실행·구조·API·데이터 설명: [시스템 동작 설명서](docs/시스템동작설명서.md)
- 새 세션 작업 맥락: [루트 AGENTS.md](AGENTS.md), [프로젝트 인수인계](docs/프로젝트인수인계.md)
- 화면 기준: `Social Impact Service UI_UX (복사)`의 Figma Make React 소스

## 현재 구현

- 청년 안부 응답과 완료 화면
- 데모 로그인, 담당 청년 목록·검색·상태 필터
- 응답률 추이, 원시 로그, 분석 근거를 포함한 상세 화면
- 알림 확인과 전담요원 처리 상태·메모 저장
- FastAPI 실제 서버와 안전한 로컬 JSON 영속화
- 규칙/AI/혼합 분석기와 AI 실패 시 자동 규칙 폴백
- 12명·720건 페르소나 시드 데이터

## 기술 스택

- Frontend: React 19, TypeScript, Vite, Tailwind CSS, Recharts
- Backend: FastAPI, Pydantic, Uvicorn
- Storage: 서버 측 JSON (`backend/data/app_data.json`)
- AI: 선택적 OpenAI Responses API 어댑터; 키가 없으면 규칙 분석

## 최초 설치

Python 3.12 이상과 Node.js 20 이상을 준비한 뒤 저장소 루트에서 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements-dev.txt
Push-Location '.\Social Impact Service UI_UX (복사)'
npm.cmd install
Pop-Location
```

## 실행

Python으로 직접 실행:

```powershell
.\.venv\Scripts\python.exe .\manage.py dev
```

또는 BAT 실행:

```bat
scripts\dev.bat
```

- 웹 화면: http://127.0.0.1:8443
- API 문서: http://127.0.0.1:8000/docs
- 종료: `Ctrl+C` 또는 Vite 터미널에서 `q`

첫 화면에서 `청년` 또는 `전담요원` 로그인을 선택합니다. 기본 데모 계정으로 로그인하면 청년은 `안부 설문 → 제출 완료`, 전담요원은 `담당 청년 → 알림 센터 → 상세·조치` 흐름으로 이동합니다.

## 데이터 초기화와 점검

```bat
scripts\reset-demo.bat
scripts\smoke-test.bat
```

같은 작업을 Python으로 직접 실행할 수도 있습니다.

```powershell
.\.venv\Scripts\python.exe .\manage.py reset
.\.venv\Scripts\python.exe .\manage.py smoke
```

스모크 테스트는 실행 중인 백엔드에 실제 데이터를 쓰므로 시연 전 `reset-demo.bat` 또는 `manage.py reset`을 한 번 더 실행하세요. BAT 파일도 PowerShell이 아니라 `manage.py`를 호출합니다.

## AI 연결 (선택)

```powershell
Copy-Item .\backend\.env.example .\backend\.env
```

`backend/.env`의 `AI_API_KEY`를 설정하면 `ANALYSIS_MODE=hybrid`에서 규칙과 AI 결과를 함께 사용합니다. 키를 브라우저 코드에 넣지 마세요. 키가 없거나 호출이 실패해도 앱은 `rule-fallback`으로 계속 동작합니다.

## 테스트

```powershell
Push-Location .\backend
..\.venv\Scripts\python.exe -m pytest
Pop-Location

Push-Location '.\Social Impact Service UI_UX (복사)'
npx.cmd tsc --noEmit
npm.cmd run build
Pop-Location
```

이 MVP는 로컬 단일 프로세스 시연 기준입니다. 실제 인증, 운영 DB, 외부 메시지, F8/F9, 배포 구성은 포함하지 않습니다.
