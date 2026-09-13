#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
자립정보ON > 지원사업 조회 크롤러

기본 동작
- 지원사업 목록을 최신 페이지부터 순회
- 목록 카드 + 상세페이지(본문/모집대상/모집인원/신청방법/첨부파일명/이미지)를 수집
- 최근 90일(기본값) 기준으로 오래된 종료 사업 제외
- 모집중/모집예정/결과발표/상시모집은 유지
- 전체 CSV/JSON + 카테고리별 CSV/JSON 저장
- 요청 간격(delay) 적용

메모(2026-09): 목록 카드는 `<a onclick="fn_edit('idx')">` 구조로 되어 있어
idx를 onclick에서 정규식으로 추출한다. 상세페이지(edit.do)는 idx만 넘기면
차단되고, 반드시 menuPos 파라미터를 함께 GET으로 보내야 정상 응답한다
(POST + idx만으로는 "비정상적 접근입니다" 오류가 난다). 첨부파일은
`cmmn_file_down(...)` JS 함수로 다운로드되는 방식이라 실제 다운로드 URL을
확보하지 못해 attachments는 항상 빈 배열로 둔다.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://jaripon.ncrc.or.kr"
LIST_URL = f"{BASE_URL}/home/kor/support/projectMng/index.do"
DETAIL_URL = f"{BASE_URL}/home/kor/support/projectMng/edit.do"
DEFAULT_PARAMS = {"menuPos": "1"}

CATEGORIES = ("경제", "주거", "진로", "건강", "법률", "기타")
STATUSES = ("모집예정", "모집중", "모집종료", "결과발표")
ACTIVE_STATUSES = {"모집예정", "모집중", "결과발표"}

ELIGIBILITY_LABELS = (
    "모집대상", "지원대상", "참가대상", "신청대상",
    "지원자격", "신청자격", "참가자격", "지원요건", "신청요건",
)
HEADCOUNT_LABELS = ("모집인원", "선발인원", "채용인원")

USER_AGENT = "Mozilla/5.0 (compatible; JaripONResearchCrawler/1.0)"


def clean_text(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def canon_label(s: str | None) -> str:
    """'분 야' -> '분야' 같이 라벨 비교용으로 공백/기호 정규화."""
    s = clean_text(s)
    return re.sub(r"[\s:·ㆍ]+", "", s)


def safe_filename(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', "_", s).strip()
    return s or "unknown"


def absolute_url(href: str | None) -> str | None:
    if not href:
        return None
    href = href.strip()
    if not href or href.startswith(("javascript:", "#", "mailto:", "tel:")):
        return None
    return urljoin(BASE_URL, href)


def text_lines(soup: BeautifulSoup) -> list[str]:
    return [clean_text(x) for x in soup.stripped_strings if clean_text(x)]


def parse_isoish_dates(text: str) -> list[date]:
    """
    YYYY-MM-DD / YYYY.MM.DD / YYYY/MM/DD 형태만 안정적으로 파싱.
    """
    if not text:
        return []
    vals = []
    for y, m, d in re.findall(r"(20\d{2})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})", text):
        try:
            vals.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    return vals


def parse_period(text: str) -> dict[str, Any]:
    raw = clean_text(text)
    evergreen = "상시" in raw
    dates = parse_isoish_dates(raw)
    start = dates[0] if dates else None
    end = dates[1] if len(dates) >= 2 else (dates[0] if dates else None)
    return {
        "raw": raw or None,
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
        "is_evergreen": evergreen,
        "headcount_raw": None,
    }


def parse_age_range(text: str) -> tuple[int | None, int | None]:
    m = re.search(r"만\s*(\d{1,2})\s*[~\-–]\s*(\d{1,2})\s*세", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d{1,2})\s*세\s*~\s*(\d{1,2})\s*세", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"만\s*(\d{1,2})\s*세\s*이상", text)
    if m:
        return int(m.group(1)), None
    m = re.search(r"만\s*(\d{1,2})\s*세\s*이하", text)
    if m:
        return None, int(m.group(1))
    return None, None


def _is_noise_line(line: str) -> bool:
    """숫자/한글/영문이 하나도 없는 순수 기호 줄(":", "-", "(" 등)."""
    return not re.search(r"[0-9가-힣A-Za-z]", line)


def extract_eligibility(content_lines: list[str]) -> dict[str, Any]:
    """
    본문 안의 '모집대상/지원대상/참가대상/신청대상/지원자격/신청자격/참가자격/
    지원요건/신청요건' 라벨 다음 텍스트를 모집대상(자격요건 포함) 원문으로
    간주하는 휴리스틱. 본문이 토큰 단위로 잘게 쪼개진
    공고(예: "-", ":" 등이 별도 줄인 경우)를 감안해 순수 기호 줄은 건너뛰고
    다음 라벨/섹션 마커("■")를 만나기 전까지 이어 붙인다.
    공고마다 서식이 달라 여전히 놓칠 수 있다.
    """
    aliases_c = {canon_label(x) for x in ELIGIBILITY_LABELS}
    for i, line in enumerate(content_lines):
        if canon_label(line) not in aliases_c:
            continue
        parts: list[str] = []
        for nxt in content_lines[i + 1: i + 12]:
            if nxt.startswith("■") or canon_label(nxt) in aliases_c:
                break
            if _is_noise_line(nxt):
                continue
            parts.append(nxt)
            if len(" ".join(parts)) >= 60:
                break
        raw = clean_text(" ".join(parts))
        if raw:
            age_min, age_max = parse_age_range(raw)
            return {"raw": raw, "age_min": age_min, "age_max": age_max}
    return {"raw": None, "age_min": None, "age_max": None}


def extract_headcount(content_lines: list[str], eligibility_raw: str | None) -> str | None:
    """
    '모집인원/선발인원/채용인원' 라벨이 따로 있으면 그 값을, 없으면
    모집대상 원문에서 'N명' 패턴을 찾아 대체한다.
    """
    aliases_c = {canon_label(x) for x in HEADCOUNT_LABELS}
    for i, line in enumerate(content_lines):
        if canon_label(line) in aliases_c and i + 1 < len(content_lines):
            v = clean_text(content_lines[i + 1])
            if v:
                return v
    if eligibility_raw:
        m = re.search(r"\d+\s*명", eligibility_raw)
        if m:
            return clean_text(m.group(0))
    return None


def extract_summary(content_lines: list[str]) -> str | None:
    """본문에서 모집대상 라벨이 나오기 전까지를 '간략한 설명'으로 사용한다."""
    aliases_c = {canon_label(x) for x in ELIGIBILITY_LABELS}
    parts = []
    for line in content_lines:
        if canon_label(line) in aliases_c:
            break
        parts.append(line)
    text = clean_text(" ".join(parts))
    return text[:300] if text else None


def find_value_after_label(lines: list[str], aliases: tuple[str, ...], start_at: int = 0) -> str | None:
    aliases_c = {canon_label(x) for x in aliases}
    for i in range(start_at, len(lines)):
        if canon_label(lines[i]) in aliases_c:
            for j in range(i + 1, min(i + 5, len(lines))):
                candidate = clean_text(lines[j])
                if candidate and canon_label(candidate) not in aliases_c:
                    return candidate
    return None


def extract_idx_from_onclick(onclick: str | None) -> str | None:
    m = re.search(r"fn_edit\(\s*['\"]?(\d+)['\"]?\s*\)", onclick or "")
    return m.group(1) if m else None


def extract_idx_from_url(url: str) -> str | None:
    m = re.search(r"[?&]idx=(\d+)", url)
    return m.group(1) if m else None


def parse_list_cards(html: str, page_url: str) -> list[dict[str, Any]]:
    """
    목록 카드 구조 (2026-09 기준):
    <a class="box" onclick="fn_edit('2105');">
      <div class="cate_wrap">...<span class="cate">모집중</span><span class="cate">진로</span></div>
      <div class="txt_box">
        <div class="tit_area"><div class="tit">제목</div></div>
        <div class="txt_area">
          <div class="txt"><div class="ft_c"><p>기 관 명</p></div><span class="cont_txt">...</span></div>
          ...
        </div>
        <div class="sub_txt">#태그1 #태그2</div>
      </div>
    </a>
    """
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for a in soup.select('a.box[onclick*="fn_edit"]'):
        idx = extract_idx_from_onclick(a.get("onclick"))
        if not idx or idx in seen:
            continue
        seen.add(idx)

        title = None
        tit_el = a.select_one(".tit_area .tit")
        if tit_el:
            title = clean_text(tit_el.get_text(" ", strip=True))
        if not title:
            img = a.find("img")
            if img:
                title = clean_text(img.get("alt"))

        status = None
        category = None
        for cate_el in a.select(".left_cate .cate"):
            t = clean_text(cate_el.get_text(" ", strip=True))
            if t in STATUSES and status is None:
                status = t
            elif t in CATEGORIES and category is None:
                category = t

        organization_name = None
        region = None
        recruit_period_raw = None
        view_count = None
        for row in a.select(".txt_area .txt"):
            label_el = row.select_one(".ft_c")
            value_el = row.select_one(".cont_txt")
            if not label_el or not value_el:
                continue
            label = canon_label(label_el.get_text(" ", strip=True))
            value = clean_text(value_el.get_text(" ", strip=True))
            if not value:
                continue
            if label == "기관명":
                organization_name = value
            elif label == "모집지역":
                region = value
            elif label == "모집기간":
                recruit_period_raw = value
            elif label == "조회수":
                digits = re.sub(r"[^\d]", "", value)
                view_count = int(digits) if digits else None

        tags: list[str] = []
        sub_txt_el = a.select_one(".sub_txt")
        if sub_txt_el:
            raw_tags = clean_text(sub_txt_el.get_text(" ", strip=True))
            tags = [clean_text(t) for t in re.findall(r"#\s*([^#]+?)(?=\s*#|$)", raw_tags)]
            tags = [t for t in tags if t]

        items.append({
            "source_id": idx,
            "source_url": f"{DETAIL_URL}?idx={idx}&menuPos=1",
            "title": title,
            "category": category,
            "status": status,
            "organization_name": organization_name,
            "region": region,
            "recruit_period_raw": recruit_period_raw,
            "view_count": view_count,
            "tags": tags,
            "list_page_url": page_url,
        })

    return items


def extract_content_text(lines: list[str]) -> str:
    """
    본문은 해시태그 줄(#로 시작) 바로 다음, 버튼 라벨(신청하기/스크랩/URL 복사/목록)을
    건너뛴 지점부터 '기관정보' 라벨 전까지로 간주한다.
    해시태그가 없는 공고는 40자 이상인 첫 문장부터 시작하는 것으로 대체한다.
    """
    drop_labels = {canon_label(x) for x in ("신청하기", "스크랩", "URL 복사", "목록")}

    hashtag_idx = None
    for i, line in enumerate(lines):
        if line.startswith("#"):
            hashtag_idx = i
            break

    start = None
    if hashtag_idx is not None:
        start = hashtag_idx + 1
        while start < len(lines) and canon_label(lines[start]) in drop_labels:
            start += 1
    else:
        for i, line in enumerate(lines):
            if len(line) >= 40 and canon_label(line) not in {"지원사업조회"}:
                start = i
                break

    if start is None:
        return ""

    end = len(lines)
    for i in range(start, len(lines)):
        if canon_label(lines[i]) == "기관정보":
            end = i
            break

    body = [x for x in lines[start:end] if canon_label(x) not in drop_labels]
    return "\n".join(body).strip()


def extract_tags(soup: BeautifulSoup, lines: list[str]) -> list[str]:
    tags: list[str] = []
    for el in soup.find_all(string=re.compile(r"^\s*#")):
        t = clean_text(str(el))
        if t.startswith("#"):
            for part in re.findall(r"#\s*([^#]+?)(?=\s*#|$)", t):
                p = clean_text(part)
                if p:
                    tags.append(p)
    if not tags:
        for line in lines:
            if line.startswith("#"):
                tags.extend(clean_text(x) for x in re.findall(r"#\s*([^#]+?)(?=\s*#|$)", line))
    out = []
    seen = set()
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def extract_images(soup: BeautifulSoup) -> list[dict[str, str | None]]:
    out = []
    seen = set()
    for img in soup.find_all("img", src=True):
        src = absolute_url(img.get("src"))
        if not src:
            continue
        low = src.lower()
        alt = clean_text(img.get("alt")) or None
        if any(x in low for x in ("logo", "loading", "/common/", "/images/common/", "ico_", "icon_")):
            continue
        if src in seen:
            continue
        seen.add(src)
        out.append({"alt": alt, "url": src})
    return out


def build_record(item: dict[str, Any]) -> dict[str, Any]:
    """상세페이지 요청이 실패했을 때 목록 카드 정보만으로 구성하는 대체 레코드."""
    period = parse_period(item.get("recruit_period_raw") or "")
    return {
        "schema_version": "1.0",
        "source": "jaripon",
        "source_id": item["source_id"],
        "source_url": item["source_url"],
        "crawled_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
        "category": item.get("category"),
        "status": item.get("status"),
        "title": item.get("title"),
        "region": item.get("region"),
        "recruitment": period,
        "application": {"method": None, "url": None},
        "result": {"announcement_date_raw": None, "confirmation": None},
        "organization": {
            "name": item.get("organization_name"),
            "manager_name": None,
            "contact": None,
        },
        "view_count": item.get("view_count"),
        "tags": item.get("tags", []),
        "eligibility": {"raw": None, "age_min": None, "age_max": None},
        "summary": None,
        "content_text": None,
        "attachments": [],
        "images": [],
        "detail_accessible": False,
    }


def parse_detail(html: str, url: str, list_item: dict[str, Any]) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    lines = text_lines(soup)

    org_start = 0
    for i, line in enumerate(lines):
        if canon_label(line) == "기관정보":
            org_start = i
            break

    category = find_value_after_label(lines, ("분야", "분 야")) or list_item.get("category")
    region = find_value_after_label(lines, ("지역", "지 역")) or list_item.get("region")
    recruit_raw = find_value_after_label(lines, ("모집기간", "모 집 기 간")) or list_item.get("recruit_period_raw")
    application_method = find_value_after_label(lines, ("접수방법", "접 수 방 법"))
    result_date_raw = find_value_after_label(lines, ("결과발표일", "결 과 발 표 일"))
    result_confirmation = find_value_after_label(lines, ("결과확인", "결 과 확 인"))

    organization_name = (
        find_value_after_label(lines, ("기관명",), start_at=org_start)
        or list_item.get("organization_name")
    )
    manager_name = find_value_after_label(lines, ("담당자명", "담당자 명"), start_at=org_start)
    contact = find_value_after_label(lines, ("문의",), start_at=org_start)

    status = list_item.get("status")
    if not status:
        early = " ".join(lines[:80])
        status = next((s for s in STATUSES if s in early), None)

    title = list_item.get("title")
    if not title:
        for h in soup.select("h1, h2, h3, h4, strong"):
            t = clean_text(h.get_text(" ", strip=True))
            if len(t) >= 5 and t not in {"지원사업 조회", "기관정보", "첨부파일"}:
                title = t
                break

    application_url = None
    for a in soup.find_all("a", href=True):
        txt = canon_label(a.get_text(" ", strip=True))
        href = absolute_url(a.get("href"))
        if href and ("신청하기" in txt or txt == "신청"):
            application_url = href
            break

    content_text = extract_content_text(lines)
    content_lines = content_text.split("\n") if content_text else []

    eligibility = extract_eligibility(content_lines)
    headcount_raw = extract_headcount(content_lines, eligibility.get("raw"))
    summary = extract_summary(content_lines)

    period = parse_period(recruit_raw or "")
    period["headcount_raw"] = headcount_raw

    return {
        "schema_version": "1.0",
        "source": "jaripon",
        "source_id": list_item.get("source_id") or extract_idx_from_url(url),
        "source_url": url,
        "crawled_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
        "category": category,
        "status": status,
        "title": title,
        "region": region,
        "recruitment": period,
        "application": {
            "method": application_method,
            "url": application_url,
        },
        "result": {
            "announcement_date_raw": result_date_raw,
            "confirmation": result_confirmation,
        },
        "organization": {
            "name": organization_name,
            "manager_name": manager_name,
            "contact": contact,
        },
        "view_count": list_item.get("view_count"),
        "tags": extract_tags(soup, lines) or list_item.get("tags", []),
        "eligibility": eligibility,
        "summary": summary,
        "content_text": content_text or None,
        "attachments": [],
        "images": extract_images(soup),
        "detail_accessible": True,
    }


def date_from_iso(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def is_recent_record(record: dict[str, Any], cutoff: date) -> bool:
    """
    '최근성'은 등록일이 아니라 모집기간/상태 기준.
    - 모집중/모집예정/결과발표: 포함
    - 상시모집: 포함
    - 모집 종료일 또는 시작일이 cutoff 이후: 포함
    - 날짜를 파싱할 수 없으면 보수적으로 포함
    """
    if record.get("status") in ACTIVE_STATUSES:
        return True

    r = record.get("recruitment", {})
    if r.get("is_evergreen"):
        return True

    start = date_from_iso(r.get("start_date"))
    end = date_from_iso(r.get("end_date"))

    if start is None and end is None:
        return True
    if end and end >= cutoff:
        return True
    if start and start >= cutoff:
        return True
    return False


def card_is_candidate(item: dict[str, Any], cutoff: date) -> bool:
    if item.get("status") in ACTIVE_STATUSES:
        return True
    p = parse_period(item.get("recruit_period_raw") or "")
    if p["is_evergreen"]:
        return True
    start = date_from_iso(p["start_date"])
    end = date_from_iso(p["end_date"])
    if start is None and end is None:
        return True
    return bool((end and end >= cutoff) or (start and start >= cutoff))


def page_looks_old(cards: list[dict[str, Any]], cutoff: date) -> bool:
    """
    페이지 조기 종료 판단.
    날짜 없는 카드/상시/활성 상태가 하나라도 있으면 old page로 보지 않는다.
    """
    if not cards:
        return True

    saw_dated = False
    for item in cards:
        if item.get("status") in ACTIVE_STATUSES:
            return False
        p = parse_period(item.get("recruit_period_raw") or "")
        if p["is_evergreen"]:
            return False
        start = date_from_iso(p["start_date"])
        end = date_from_iso(p["end_date"])
        if start is None and end is None:
            return False
        saw_dated = True
        if (end and end >= cutoff) or (start and start >= cutoff):
            return False
    return saw_dated


@dataclass
class PageFetcher:
    session: requests.Session
    delay: float
    first_html: str
    page_param: str | None = None

    def _sleep(self):
        if self.delay > 0:
            time.sleep(self.delay)

    def _get(self, params: dict[str, Any]) -> requests.Response:
        self._sleep()
        r = self.session.get(LIST_URL, params=params, timeout=30)
        r.raise_for_status()
        return r

    def _post(self, data: dict[str, Any]) -> requests.Response:
        self._sleep()
        r = self.session.post(LIST_URL, data=data, timeout=30)
        r.raise_for_status()
        return r

    def discover_page_param(self) -> str:
        soup = BeautifulSoup(self.first_html, "html.parser")

        names = [
            x.get("name") for x in soup.find_all(["input", "select"])
            if x.get("name") and re.search(r"page", x.get("name"), re.I)
        ]
        preferred = ["pageIndex", "pageNo", "page", "curPage", "currentPage"]
        candidates = []
        for p in preferred + names:
            if p and p not in candidates:
                candidates.append(p)

        script_text = "\n".join(s.get_text("\n", strip=False) for s in soup.find_all("script"))
        for m in re.findall(r"\.([A-Za-z_][A-Za-z0-9_]*page[A-Za-z0-9_]*)\.value", script_text, flags=re.I):
            if m not in candidates:
                candidates.insert(0, m)

        first_ids = {x["source_id"] for x in parse_list_cards(self.first_html, LIST_URL)}
        for candidate in candidates:
            for method in ("get", "post"):
                payload = dict(DEFAULT_PARAMS)
                payload[candidate] = "2"
                try:
                    r = self._get(payload) if method == "get" else self._post(payload)
                except requests.RequestException:
                    continue
                ids = {x["source_id"] for x in parse_list_cards(r.text, r.url)}
                if ids and ids != first_ids:
                    self.page_param = candidate
                    return candidate

        raise RuntimeError(
            "페이지네이션 파라미터를 자동 탐지하지 못했습니다. "
            "브라우저 개발자도구 Network에서 2페이지 요청의 파라미터를 확인해 "
            "--page-param 옵션으로 지정해주세요."
        )

    def fetch(self, page_no: int) -> tuple[str, str]:
        if page_no == 1:
            return self.first_html, f"{LIST_URL}?{urlencode(DEFAULT_PARAMS)}"

        if not self.page_param:
            self.discover_page_param()

        params = dict(DEFAULT_PARAMS)
        params[self.page_param] = str(page_no)
        r = self._get(params)
        return r.text, r.url


def check_robots(session: requests.Session) -> None:
    url = f"{BASE_URL}/robots.txt"
    try:
        r = session.get(url, timeout=15)
    except requests.RequestException as e:
        print(f"[robots] 확인 실패(계속 진행): {e}")
        return

    if r.status_code == 200 and r.text.strip():
        rp = RobotFileParser()
        rp.set_url(url)
        rp.parse(r.text.splitlines())
        allowed = rp.can_fetch(USER_AGENT, LIST_URL)
        print(f"[robots] robots.txt 확인: {'허용' if allowed else '비허용'}")
        if not allowed:
            raise RuntimeError("robots.txt에서 이 경로의 크롤링을 허용하지 않습니다.")
    else:
        print(f"[robots] robots.txt 명시 규칙을 확인하지 못함 (HTTP {r.status_code}).")


def flatten_for_csv(r: dict[str, Any]) -> dict[str, Any]:
    recruitment = r.get("recruitment", {})
    app = r.get("application", {})
    result = r.get("result", {})
    org = r.get("organization", {})
    eligibility = r.get("eligibility", {})
    return {
        "schema_version": r.get("schema_version"),
        "source": r.get("source"),
        "source_id": r.get("source_id"),
        "source_url": r.get("source_url"),
        "crawled_at": r.get("crawled_at"),
        "category": r.get("category"),
        "status": r.get("status"),
        "title": r.get("title"),
        "region": r.get("region"),
        "recruit_period_raw": recruitment.get("raw"),
        "recruit_start_date": recruitment.get("start_date"),
        "recruit_end_date": recruitment.get("end_date"),
        "is_evergreen": recruitment.get("is_evergreen"),
        "recruit_headcount_raw": recruitment.get("headcount_raw"),
        "application_method": app.get("method"),
        "application_url": app.get("url"),
        "result_announcement_date_raw": result.get("announcement_date_raw"),
        "result_confirmation": result.get("confirmation"),
        "organization_name": org.get("name"),
        "manager_name": org.get("manager_name"),
        "contact": org.get("contact"),
        "view_count": r.get("view_count"),
        "tags_json": json.dumps(r.get("tags", []), ensure_ascii=False),
        "eligibility_raw": eligibility.get("raw"),
        "eligibility_age_min": eligibility.get("age_min"),
        "eligibility_age_max": eligibility.get("age_max"),
        "summary": r.get("summary"),
        "content_text": r.get("content_text"),
        "attachments_json": json.dumps(r.get("attachments", []), ensure_ascii=False),
        "images_json": json.dumps(r.get("images", []), ensure_ascii=False),
        "detail_accessible": r.get("detail_accessible"),
    }


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    flat = [flatten_for_csv(x) for x in rows]
    if not flat:
        path.write_text("", encoding="utf-8-sig")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(flat[0].keys()))
        w.writeheader()
        w.writerows(flat)


def save_outputs(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "jaripon_all.json", rows)
    write_csv(output_dir / "jaripon_all.csv", rows)

    by_dir = output_dir / "by_category"
    by_dir.mkdir(exist_ok=True)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("category") or "미분류", []).append(row)

    for category, items in sorted(grouped.items()):
        name = safe_filename(category)
        write_json(by_dir / f"{name}.json", items)
        write_csv(by_dir / f"{name}.csv", items)


def crawl(args: argparse.Namespace) -> list[dict[str, Any]]:
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    cutoff = today - timedelta(days=args.days)
    print(f"[기준] 오늘={today.isoformat()} / 최근 {args.days}일 cutoff={cutoff.isoformat()}")

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
    })

    if not args.skip_robots:
        check_robots(session)

    print("[목록] 1페이지 요청")
    r = session.get(LIST_URL, params=DEFAULT_PARAMS, timeout=30)
    r.raise_for_status()
    fetcher = PageFetcher(session=session, delay=args.delay, first_html=r.text, page_param=args.page_param)

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    old_streak = 0

    for page_no in range(1, args.max_pages + 1):
        try:
            html, page_url = fetcher.fetch(page_no)
        except Exception as e:
            print(f"[중단] {page_no}페이지 조회 실패: {e}")
            break

        cards = parse_list_cards(html, page_url)
        new_cards = [x for x in cards if x["source_id"] not in seen_ids]
        print(f"[목록] page={page_no} cards={len(cards)} new={len(new_cards)}")

        if page_no > 1 and not new_cards:
            print("[중단] 새 게시물이 없어 페이지 순회를 종료합니다.")
            break

        if page_looks_old(cards, cutoff):
            old_streak += 1
        else:
            old_streak = 0

        for item in new_cards:
            seen_ids.add(item["source_id"])

            if args.categories and (item.get("category") not in args.categories):
                if item.get("category") is not None:
                    continue

            if not card_is_candidate(item, cutoff):
                continue

            time.sleep(args.delay)
            try:
                d = session.get(
                    DETAIL_URL,
                    params={"idx": item["source_id"], "menuPos": "1"},
                    headers={"Referer": page_url},
                    timeout=30,
                )
                d.raise_for_status()
                record = parse_detail(d.text, d.url, item)
            except requests.RequestException as e:
                print(f"  ! 상세 요청 실패 id={item['source_id']}: {e}")
                record = build_record(item)
            except Exception as e:
                print(f"  ! 상세 파싱 실패 id={item['source_id']}: {e}")
                record = build_record(item)

            if args.categories and record.get("category") not in args.categories:
                continue

            if is_recent_record(record, cutoff):
                rows.append(record)
                print(f"  + [{record.get('category')}] {record.get('title')}")

        if old_streak >= args.old_page_streak:
            print(f"[중단] 오래된 페이지가 {old_streak}개 연속이라 조기 종료합니다.")
            break

    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        dedup[row["source_id"]] = row
    rows = list(dedup.values())

    def sort_key(x: dict[str, Any]):
        r = x.get("recruitment", {})
        return (r.get("start_date") or "", x.get("source_id") or "")

    rows.sort(key=sort_key, reverse=True)
    return rows


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="자립정보ON 지원사업 크롤러")
    p.add_argument("--days", type=int, default=90, help="최근 범위. 기본 90일")
    p.add_argument("--delay", type=float, default=1.2, help="요청 간격(초). 기본 1.2")
    p.add_argument("--max-pages", type=int, default=40, help="안전상 최대 목록 페이지 수")
    p.add_argument(
        "--old-page-streak", type=int, default=2,
        help="오래된 목록 페이지가 N개 연속이면 조기 종료. 기본 2"
    )
    p.add_argument("--output-dir", default="jaripon_output", help="저장 폴더")
    p.add_argument(
        "--categories", nargs="*", choices=CATEGORIES,
        help="특정 카테고리만 수집. 예: --categories 경제 주거"
    )
    p.add_argument(
        "--page-param", default=None,
        help="페이지네이션 파라미터를 알고 있을 때 직접 지정 (예: pageIndex)"
    )
    p.add_argument(
        "--skip-robots", action="store_true",
        help="robots.txt 자동 확인을 건너뜀 (권장하지 않음)"
    )
    return p


def main():
    args = build_parser().parse_args()
    rows = crawl(args)
    output_dir = Path(args.output_dir)
    save_outputs(output_dir, rows)
    print(f"\n[완료] {len(rows)}건 저장")
    print(f"  JSON: {output_dir / 'jaripon_all.json'}")
    print(f"  CSV : {output_dir / 'jaripon_all.csv'}")
    print(f"  카테고리별: {output_dir / 'by_category'}")


if __name__ == "__main__":
    main()
