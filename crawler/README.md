# 자립정보ON 지원사업 크롤러

## ⚠️ 목록 카드만 수집 (상세페이지 미접근)

원래는 상세페이지 본문까지 수집하도록 설계됐으나, 실제 사이트 점검 결과 두 가지 이슈가 확인되어 **목록 카드 정보만 수집**하도록 수정했다.

1. 목록 페이지 HTML이 `<a href="...edit.do?idx=...">` 구조에서 `<a onclick="fn_edit('idx')">` 구조로 바뀌어 있었다. → 목록 파서를 새 구조에 맞게 수정함.
2. 상세페이지(`/home/kor/support/projectMng/edit.do`)는 GET/POST 어떤 방식으로 요청해도 (세션 쿠키·Referer 포함) `"비정상적 접근입니다"` 응답과 함께 차단된다. 페이지에 reCAPTCHA 스크립트가 로드되는 것으로 보아 서버 측 자동화 차단 장치로 판단되며, 우회를 시도하지 않았다.

그 결과 `content_text`(본문), `attachments`(첨부파일), `images`, `application`(신청 URL), `result`(결과발표)는 **항상 null 또는 빈 배열**이고, `detail_accessible`은 항상 `false`다. 대신 목록 카드에 이미 포함된 제목/분야/상태/기관명/지역/모집기간/조회수/해시태그는 정상 수집된다.

## 기본 실행

```bash
pip install -r requirements.txt
python jaripon_crawler.py
```

기본값은 **최근 90일**입니다.

```bash
python jaripon_crawler.py --days 90
```

최근 60일만:

```bash
python jaripon_crawler.py --days 60
```

경제/주거만:

```bash
python jaripon_crawler.py --days 90 --categories 경제 주거
```

## 출력

```text
jaripon_output/
├─ jaripon_all.json
├─ jaripon_all.csv
└─ by_category/
   ├─ 경제.json
   ├─ 경제.csv
   ├─ 주거.json
   ├─ 주거.csv
   └─ ...
```

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

- `recruitment`: 모집기간
- `application`: 접수방법/신청 URL (항상 null)
- `result`: 결과발표/확인 (항상 null)
- `organization`: 기관명/담당자/문의 (담당자·문의는 항상 null)
- `tags`: 배열 (목록 카드의 해시태그)
- `attachments`: 배열 (항상 빈 배열)
- `images`: 배열 (항상 빈 배열)
- `content_text`: 상세 본문 전체 (항상 null)
- `detail_accessible`: 상세페이지 접근 성공 여부 (항상 false)

CSV는 분석 편의를 위해 위 구조를 평탄화하고,
배열(`tags`, `attachments`, `images`)은 JSON 문자열로 셀에 저장합니다.

## 운영 팁

- 요청 간격 기본 1.2초. 서버 부담을 줄이려면 더 늘리세요.
- `robots.txt`에 명시적 차단이 있으면 기본적으로 중단합니다.
- 사이트 HTML 구조가 바뀌면 선택자/라벨 파서 조정이 필요할 수 있습니다.
- 페이지네이션 자동 탐지가 실패하면 브라우저 개발자도구 Network에서
  2페이지 요청의 페이지 파라미터를 확인한 뒤 예를 들어:

```bash
python jaripon_crawler.py --page-param pageIndex
```
