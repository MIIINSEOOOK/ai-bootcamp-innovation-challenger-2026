# jaripon 지원사업 데이터 스냅샷

`crawler/jaripon_crawler.py`로 수집한 자립정보ON(jaripon.ncrc.or.kr) 지원사업 목록 스냅샷.

- 수집일: 2026-09-13
- 수집 건수: 224건 (진로 100 · 기타 69 · 경제 24 · 건강 12 · 주거 12 · 법률 7)
- 범위: 최근 90일 (기본값)
- 상세페이지 접근이 차단되어 있어 목록 카드 정보만 포함 (`content_text`/`attachments`/`images`는 항상 null·빈 배열, `detail_accessible: false`). 자세한 내용은 `crawler/README.md` 참고.

## 용도

실제 청년 개인정보가 아닌 **공개 지원제도 정보**로, 페르소나 설계 시 "이 페르소나가 참고할 만한 실제 지원제도" 배경 자료로 활용하기 위한 데이터. F9(지원제도 매칭)의 향후 확장이나, 페르소나의 자립상태 프로필에 현실성을 부여하는 용도로 사용한다.

## 갱신

```bash
cd crawler
python jaripon_crawler.py --output-dir ../data/jaripon
```
