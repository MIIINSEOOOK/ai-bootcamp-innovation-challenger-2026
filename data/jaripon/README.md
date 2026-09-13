# jaripon 지원사업 데이터 스냅샷

자립정보ON(jaripon.ncrc.or.kr)의 지원사업 목록+상세 정보를 수집한 정적 스냅샷. 실제 청년 개인정보가 아니라 누구나 볼 수 있는 **공개 지원제도 공고**만 담고 있다.

- 수집일: 2026-09-13
- 수집 건수: 224건 (진로 100 · 기타 69 · 경제 24 · 건강 12 · 주거 12 · 법률 7)
- 범위: 최근 90일

## 디렉토리 구조

```text
data/jaripon/
├─ README.md              # 이 파일
├─ schema.json             # 레코드 JSON Schema
├─ jaripon_all.json        # 전체 224건, 구조화된 JSON (배열)
├─ jaripon_all.csv         # 전체 224건, 평탄화된 CSV (UTF-8 BOM)
└─ by_category/            # jaripon_all.* 을 category 기준으로 나눈 것 (내용은 동일 스키마)
   ├─ 경제.json / 경제.csv
   ├─ 주거.json / 주거.csv
   ├─ 진로.json / 진로.csv
   ├─ 건강.json / 건강.csv
   ├─ 법률.json / 법률.csv
   └─ 기타.json / 기타.csv   # 카테고리 미분류 항목도 여기 포함
```

레코드 필드: `title`/`category`/`status`/`region`/`recruitment`/`eligibility`/`summary`/`content_text`/`organization`/`application`/`result`/`tags`/`view_count`/`detail_accessible` 등. 자세한 타입은 `schema.json` 참고.

## 한계 / 주의사항

224건 모두 상세페이지 접근에는 성공했다(`detail_accessible: true`). 다만 다음 필드들은 **본문에 해당 라벨이 명시된 공고에서만** 채워지는 라벨 기반 휴리스틱 추출이라 커버리지가 낮다:

- `eligibility`(모집대상/지원자격/지원요건): 224건 중 16건만 채워짐
- `recruitment.headcount_raw`(모집인원): 224건 중 9건만 채워짐
- 이미지/포스터 위주로 올라온 공고(본문에 텍스트가 거의 없는 경우)는 위 필드가 아예 비어있다.

그 외 알려진 한계:

- `content_text`: 사이트 에디터가 문장을 토큰 단위로 쪼개 저장한 공고가 있어(예: "20" "-" "29" "세"가 각각 별도 줄) 줄바꿈이 다소 부자연스러울 수 있다.
- `attachments`: 항상 빈 배열. 첨부파일이 `cmmn_file_down(...)` JS 함수로 다운로드되는 방식이라 실제 다운로드 URL을 수집하지 못했다.
- `images`: 로고/아이콘을 제외한 본문 삽입 이미지만 best-effort로 수집(대부분 비어있음).

## 용도

페르소나 설계 시 "이 페르소나가 참고할 만한 실제 지원제도" 배경 자료로 활용하기 위한 데이터. F9(지원제도 매칭)의 향후 확장이나, 페르소나의 자립상태 프로필(모집대상 연령/조건과 실제로 맞아떨어지는 지원제도)에 현실성을 부여하는 용도로 사용한다.

## 수집 방법

목록 페이지(`GET .../projectMng/index.do`)를 페이지네이션하며 카드를 파싱하고, 각 항목의 상세페이지(`GET .../projectMng/edit.do?idx=<id>&menuPos=1`)를 요청해 본문/모집대상/신청URL 등을 라벨 기반 휴리스틱으로 추출했다. `menuPos` 파라미터 없이는 상세페이지가 `"비정상적 접근입니다"`로 막히는데, 이는 봇 차단이 아니라 단순 필수 파라미터 누락이었다. `robots.txt` 확인과 요청 간 지연(1.2초)을 지켰다.

수집 스크립트는 재사용 필요가 없어 저장소에서 제거했다 — 이 스냅샷이 유일한 소스다. 데이터를 다시 수집하려면 위 방식(목록 페이지네이션 + 상세 GET with idx/menuPos)을 참고해 새로 작성하면 된다.
