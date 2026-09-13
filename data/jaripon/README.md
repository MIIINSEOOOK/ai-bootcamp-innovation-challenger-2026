# jaripon 지원사업 데이터 스냅샷

`crawler/jaripon_crawler.py`로 수집한 자립정보ON(jaripon.ncrc.or.kr) 지원사업 목록+상세 스냅샷.

- 수집일: 2026-09-13
- 수집 건수: 224건 (진로 100 · 기타 69 · 경제 24 · 건강 12 · 주거 12 · 법률 7)
- 범위: 최근 90일 (기본값)
- 224건 모두 상세페이지 접근 성공(`detail_accessible: true`). 다만 `eligibility`(모집대상/지원자격)는 16건, `recruitment.headcount_raw`(모집인원)는 9건에서만 추출됨 — 본문에 해당 라벨이 명시된 공고만 채워지는 라벨 기반 휴리스틱의 한계. 자세한 내용은 `crawler/README.md` 참고.

## 디렉토리 구조

```text
data/jaripon/
├─ README.md              # 이 파일
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

레코드 하나의 필드 구조는 `crawler/schema.json` 참고 (`title`/`category`/`status`/`region`/`recruitment`/`eligibility`/`summary`/`content_text`/`organization`/`application`/`result`/`tags`/`view_count`/`detail_accessible` 등).

## 용도

실제 청년 개인정보가 아닌 **공개 지원제도 정보**로, 페르소나 설계 시 "이 페르소나가 참고할 만한 실제 지원제도" 배경 자료로 활용하기 위한 데이터. F9(지원제도 매칭)의 향후 확장이나, 페르소나의 자립상태 프로필(모집대상 연령/조건과 실제로 맞아떨어지는 지원제도)에 현실성을 부여하는 용도로 사용한다.

## 갱신

```bash
cd crawler
python jaripon_crawler.py --output-dir ../data/jaripon
```
