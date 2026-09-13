# 자립정보ON 지원사업 크롤러

## 목록 + 상세페이지 모두 수집

목록 카드(제목/분야/상태/기관명/지역/모집기간/조회수/해시태그)와 상세페이지 본문(모집대상/모집인원/신청방법/신청URL/결과발표/문의처/본문 요약)을 함께 수집한다.

### 겪었던 이슈와 해결

1. 목록 페이지 HTML이 `<a href="...edit.do?idx=...">` 구조에서 `<a onclick="fn_edit('idx')">` 구조로 바뀌어 있었다. → 목록 파서를 onclick에서 idx를 정규식으로 뽑아내도록 수정.
2. 상세페이지(`/home/kor/support/projectMng/edit.do`)에 `idx`만 GET/POST로 보내면 `"비정상적 접근입니다"`로 차단된다. **`menuPos=1` 파라미터를 GET 쿼리에 함께 보내야 정상 응답한다** (세션 쿠키나 Referer는 없어도 무방 — 봇 차단이 아니라 필수 파라미터 누락 문제였다).
3. 첨부파일은 `<a onclick="cmmn_file_down('원본파일명','저장파일명')">` 형태라 실제 다운로드 URL을 코드만으로 확보하지 못했다. → `attachments`는 항상 빈 배열로 둔다 (파일명 자체는 미수집).

### 여전히 남는 한계

- `모집대상`(`eligibility`)·`모집인원`(`recruitment.headcount_raw`)·`간략한 설명`(`summary`)은 본문에 **"모집대상/지원대상/참가대상/신청대상" 라벨이 명시된 공고에서만** 라벨 기반 휴리스틱으로 추출된다. 이미지/포스터 위주로 올라온 공고(본문에 텍스트가 거의 없는 경우)는 채워지지 않는다.
- `content_text`는 사이트 에디터가 문장을 토큰 단위로 쪼개 저장한 경우가 있어(예: "20" "-" "29" "세"가 각각 별도 줄) 줄바꿈이 다소 부자연스러울 수 있다.
- `attachments`는 항상 빈 배열, `images`는 로고/아이콘을 제외한 본문 삽입 이미지만 best-effort로 수집한다.
- 이 두 이슈 모두 `detail_accessible: true`인 레코드에도 해당하는 한계다. `detail_accessible: false`는 상세 요청 자체가 실패해 목록 카드 정보만 들어간 경우다.

페르소나 제작 시 모집인원·모집대상·설명이 비어 있는 공고는 해당 공고를 브라우저로 열어 수동으로 보완해야 한다.

## 기본 실행

```bash
pip install -r requirements.txt
python jaripon_crawler.py --output-dir ../data/jaripon
```

`--output-dir`을 생략하면 현재 디렉토리(`crawler/`) 밑에 `jaripon_output/`을 만든다 (`.gitignore`에 등록되어 있어 커밋되지 않는다). 이 저장소의 정식 스냅샷은 `../data/jaripon`에 커밋되므로, 스냅샷을 갱신할 때는 항상 `--output-dir ../data/jaripon`을 지정한다.

기본값은 **최근 90일**입니다.

```bash
python jaripon_crawler.py --days 90 --output-dir ../data/jaripon
```

최근 60일만:

```bash
python jaripon_crawler.py --days 60 --output-dir ../data/jaripon
```

경제/주거만:

```bash
python jaripon_crawler.py --days 90 --categories 경제 주거 --output-dir ../data/jaripon
```

## 출력

`--output-dir`로 지정한 경로(정식 스냅샷은 `../data/jaripon`, 즉 저장소 기준 `data/jaripon/`) 아래에 다음 구조로 저장된다.

```text
data/jaripon/
├─ jaripon_all.json
├─ jaripon_all.csv
└─ by_category/
   ├─ 경제.json
   ├─ 경제.csv
   ├─ 주거.json
   ├─ 주거.csv
   └─ ...
```

디렉토리 구조와 각 파일의 의미는 `../data/jaripon/README.md`에 더 자세히 정리되어 있다.

## 최근 90일의 의미

자립정보ON 공개 목록에는 별도 `등록일` 필드가 노출되지 않으므로,
이 크롤러는 `모집기간 + 모집상태`를 최근성 판단 기준으로 사용합니다.

포함:
- 모집중
- 모집예정
- 결과발표
- 상시 모집
- 모집 시작일 또는 종료일이 cutoff 이후인 사업

제외:
- 모집종료 상태이면서 시작/종료일이 모두 cutoff보다 오래된 사업

## 스키마 원칙

JSON은 구조를 보존합니다.

- `recruitment`: 모집기간 (`headcount_raw`=모집인원, 라벨 있는 공고만)
- `application`: 접수방법/신청 URL
- `result`: 결과발표/확인
- `organization`: 기관명/담당자/문의
- `tags`: 배열 (해시태그)
- `eligibility`: 모집대상 원문 + 추출된 연령(`age_min`/`age_max`), 라벨 있는 공고만
- `summary`: 공고 간략 설명(본문에서 모집대상 라벨 전까지)
- `attachments`: 배열 (항상 빈 배열 — 다운로드 URL 미해결)
- `images`: 배열 (본문 삽입 이미지, best-effort)
- `content_text`: 상세 본문 전체
- `detail_accessible`: 상세페이지 요청이 성공했는지 여부

CSV는 분석 편의를 위해 위 구조를 평탄화하고,
배열(`tags`, `attachments`, `images`)은 JSON 문자열로 셀에 저장합니다.

## 운영 팁

- 요청 간격 기본 1.2초 (목록 페이지 요청 + 후보 항목별 상세 요청 각각에 적용). 서버 부담을 줄이려면 더 늘리세요.
- `robots.txt`에 명시적 차단이 있으면 기본적으로 중단합니다.
- 사이트 HTML 구조가 바뀌면 선택자/라벨 파서 조정이 필요할 수 있습니다.
- 페이지네이션 자동 탐지가 실패하면 브라우저 개발자도구 Network에서
  2페이지 요청의 페이지 파라미터를 확인한 뒤 예를 들어:

```bash
python jaripon_crawler.py --page-param pageIndex
```
