import { useEffect, useState } from "react";
import { api, errorMessage } from "../lib/api";
import type { StatusLabel, YouthListItem } from "../types";

interface Props {
  onSelectYouth: (youthId: string) => void;
  onAlerts: () => void;
}

const STATUS_CONFIG: Record<StatusLabel, { bg: string; text: string; dot: string }> = {
  "정상": { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  "관심 필요": { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  "훼손 의심": { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
};

function formatLastResponse(value: string | null): string {
  if (!value) return "응답 없음";
  const today = new Date();
  const target = new Date(`${value}T00:00:00`);
  const days = Math.max(0, Math.floor((today.getTime() - target.getTime()) / 86_400_000));
  if (days === 0) return "오늘";
  if (days === 1) return "어제";
  return `${days}일 전`;
}

export default function WorkerList({ onSelectYouth, onAlerts }: Props) {
  const [filter, setFilter] = useState<StatusLabel | "전체">("전체");
  const [search, setSearch] = useState("");
  const [allYouths, setAllYouths] = useState<YouthListItem[]>([]);
  const [filtered, setFiltered] = useState<YouthListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listYouths()
      .then(setAllYouths)
      .catch((caught) => setError(errorMessage(caught)));
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const timer = window.setTimeout(() => {
      api.listYouths(search, filter === "전체" ? "" : filter)
        .then((items) => active && setFiltered(items))
        .catch((caught) => active && setError(errorMessage(caught)))
        .finally(() => active && setLoading(false));
    }, 180);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [filter, search]);

  const alertCount = allYouths.filter((youth) => youth.hasAlert).length;

  const counts = {
    "전체": allYouths.length,
    "정상": allYouths.filter((y) => y.status === "정상").length,
    "관심 필요": allYouths.filter((y) => y.status === "관심 필요").length,
    "훼손 의심": allYouths.filter((y) => y.status === "훼손 의심").length,
  };

  return (
    <div className="w-full max-w-[1100px]">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-1 text-xs font-bold tracking-[0.14em] text-[#3B6EBE]">YOUTH CARE</p>
          <h1 className="text-2xl font-bold text-[#1A2340]">담당 청년 현황</h1>
          <p className="mt-2 text-sm text-slate-400">응답 변화와 지원이 필요한 대상을 한눈에 확인하세요.</p>
        </div>
        <button onClick={onAlerts} className="relative flex items-center justify-center gap-2 rounded-xl border border-red-100 bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-600 transition-all hover:border-red-200 hover:bg-red-100">
          확인할 알림 <span className="rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-bold text-white">{alertCount}</span>
        </button>
      </div>

      {/* Summary cards */}
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        {(["전체", "정상", "관심 필요", "훼손 의심"] as const).map((s) => {
          const cfg = s === "전체"
            ? { dot: "bg-slate-400", bg: "bg-white", text: "text-slate-700" }
            : STATUS_CONFIG[s];
          return (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-5 py-4 rounded-2xl border-2 text-left transition-all ${
                filter === s
                  ? s === "전체"
                    ? "border-[#3B6EBE] bg-[#3B6EBE]/5"
                    : `border-current ${cfg.bg} ${cfg.text}`
                  : "border-transparent bg-white hover:border-slate-200"
              } shadow-sm`}
            >
              <div className="flex items-center gap-2 mb-1">
                <div className={`w-2 h-2 rounded-full ${s === "전체" ? "bg-slate-400" : cfg.dot}`} />
                <span className="text-xs font-medium text-slate-500">{s}</span>
              </div>
              <span className="text-2xl font-bold text-[#1A2340]">{counts[s]}</span>
              <span className="text-xs text-slate-400 ml-1">명</span>
            </button>
          );
        })}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white shadow-sm">
        {/* Table header bar */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[#1A2340]">담당 청년 목록</h2>
          <div className="flex items-center gap-3">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                width="14" height="14" viewBox="0 0 14 14" fill="none"
              >
                <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M9.5 9.5L12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <input
                type="text"
                placeholder="이름 또는 지역 검색"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-[#3B6EBE] w-44 bg-slate-50 transition-all"
              />
            </div>
            <span className="text-xs text-slate-400">
              {filtered.length}명 표시
            </span>
          </div>
        </div>

        <table className="w-full min-w-[900px]">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-100">
              <th className="text-left px-6 py-3 text-xs font-semibold text-slate-400 tracking-wide">이름</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 tracking-wide">나이</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 tracking-wide">거주 지역</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 tracking-wide">현재 상태</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 tracking-wide">응답률</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 tracking-wide">마지막 응답</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 tracking-wide">알림</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filtered.map((y) => {
              const cfg = STATUS_CONFIG[y.status];
              return (
                <tr
                  key={y.youthId}
                  className="hover:bg-slate-50/70 transition-colors cursor-pointer group"
                  onClick={() => onSelectYouth(y.youthId)}
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#6BA8A9] to-[#3B6EBE] text-white text-xs font-bold flex items-center justify-center shadow-sm">
                        {y.name[0]}
                      </div>
                      <span className="text-sm font-semibold text-[#1A2340]">{y.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-500">{y.age}세</td>
                  <td className="px-4 py-4 text-sm text-slate-500">{y.region}</td>
                  <td className="px-4 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                      {y.status}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            y.responseRate >= 75
                              ? "bg-emerald-400"
                              : y.responseRate >= 50
                              ? "bg-amber-400"
                              : "bg-red-400"
                          }`}
                          style={{ width: `${Math.round(y.responseRate)}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-slate-600">{Math.round(y.responseRate)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-500">{formatLastResponse(y.lastResponseAt)}</td>
                  <td className="px-4 py-4">
                    {y.hasAlert ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-50 text-red-600 text-xs font-semibold rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                        있음
                      </span>
                    ) : (
                      <span className="text-xs text-slate-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-xs text-[#3B6EBE] font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                      상세보기 →
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {loading && (
          <div className="py-12 text-center text-sm text-slate-400">목록을 불러오는 중...</div>
        )}
        {!loading && error && (
          <div role="alert" className="py-12 text-center text-sm text-red-500">{error}</div>
        )}
        {!loading && !error && filtered.length === 0 && (
          <div className="py-12 text-center text-sm text-slate-400">
            검색 결과가 없습니다
          </div>
        )}
      </div>
    </div>
  );
}
