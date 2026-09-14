import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, errorMessage } from "../lib/api";
import type { ActionStatus, CheckinRecord, StatusLabel, YouthDetail } from "../types";

interface Props {
  youthId: string;
  onBack: () => void;
}

const STATUS_CONFIG: Record<StatusLabel, { bg: string; text: string; dot: string }> = {
  "정상": { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  "관심 필요": { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  "훼손 의심": { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
};

const MOOD_CONFIG: Record<string, string> = {
  "좋음": "😊", "좋아요": "😊", "보통": "😐", "그냥 그래요": "😐",
  "힘듦": "😔", "좀 힘들어요": "😔", "매우 힘듦": "😞", "많이 힘들어요": "😞",
};

function responseTrend(checkins: CheckinRecord[]) {
  const records = [...checkins].filter((item) => item.sent).sort((a, b) => a.date.localeCompare(b.date)).slice(-49);
  const chunks: CheckinRecord[][] = [];
  for (let index = 0; index < records.length; index += 7) chunks.push(records.slice(index, index + 7));
  return chunks.map((chunk) => ({
    period: chunk.at(-1)?.date.slice(5).replace("-", "/") ?? "-",
    rate: Math.round(chunk.filter((item) => item.responded).length / chunk.length * 100),
  }));
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-xl px-3 py-2 shadow-lg text-xs">
      <p className="font-semibold text-slate-600">{label}</p>
      <p className="text-[#3B6EBE] font-bold">{payload[0].value}%</p>
    </div>
  );
}

export default function WorkerDetail({ youthId, onBack }: Props) {
  const [data, setData] = useState<YouthDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [processStatus, setProcessStatus] = useState<ActionStatus | null>(null);
  const [memo, setMemo] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const detail = await api.getYouth(youthId);
      setData(detail);
      setProcessStatus(detail.caseActions[0]?.status ?? null);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [youthId]);

  const trend = useMemo(() => responseTrend(data?.checkins ?? []), [data]);

  const saveAction = async () => {
    if (!processStatus) return;
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const action = await api.createAction(youthId, processStatus, memo);
      setData((current) => current ? { ...current, caseActions: [action, ...current.caseActions] } : current);
      setSaved(true);
      setMemo("");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSaving(false);
    }
  };

  const runAnalysis = async () => {
    setAnalyzing(true);
    setError("");
    try {
      await api.analyze(youthId);
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading && !data) {
    return <div className="w-full max-w-[1100px] bg-white rounded-2xl py-20 text-center text-sm text-slate-400">상세 정보를 불러오는 중...</div>;
  }
  if (!data) {
    return (
      <div className="w-full max-w-[780px] bg-white rounded-2xl py-16 text-center text-sm text-red-500">
        <p>{error || "상세 정보를 표시할 수 없습니다."}</p>
        <button onClick={onBack} className="mt-4 text-[#3B6EBE] font-semibold">목록으로 돌아가기</button>
      </div>
    );
  }

  const { youth, metrics, assessment, checkins } = data;
  const cfg = STATUS_CONFIG[assessment.label];
  const logs = checkins.filter((item) => item.responded).slice(0, 8);
  const fallback = assessment.analyzer === "rule-fallback";

  return (
    <div className="w-full max-w-[1100px]">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-400 hover:text-[#3B6EBE] transition-colors">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8L10 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            목록으로
          </button>
          <span className="text-slate-300">|</span>
          <h1 className="text-xl font-bold text-[#1A2340]">청년 상세 정보</h1>
        </div>
        <button onClick={runAnalysis} disabled={analyzing} className="px-4 py-2 text-xs font-semibold text-white bg-[#3B6EBE] rounded-lg hover:bg-[#2E5BA8] disabled:bg-slate-300">
          {analyzing ? "분석 중..." : "상태 다시 분석"}
        </button>
      </div>

      {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
      {fallback && (
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-700">
          AI 키가 없거나 호출에 실패해 규칙 분석 결과를 표시합니다. 데이터 저장과 판정 흐름은 정상 동작 중입니다.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="space-y-4">
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#6BA8A9] to-[#3B6EBE] text-white text-xl font-bold flex items-center justify-center shadow-md">{youth.name[0]}</div>
              <div>
                <h2 className="text-lg font-bold text-[#1A2340]">{youth.name}</h2>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />{assessment.label}
                </span>
              </div>
            </div>
            <div className="space-y-2.5">
              {[
                ["나이", `${youth.age}세`], ["거주 지역", youth.region], ["주거", youth.independenceStatus.housing],
                ["취업·교육", youth.independenceStatus.employmentEducation], ["담당 요원", youth.caseWorker], ["보호 종료일", youth.independenceStatus.careExitDate],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between items-center gap-3"><span className="text-xs text-slate-400">{label}</span><span className="text-xs font-medium text-[#1A2340] text-right">{value}</span></div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-slate-100">
              <div className="flex justify-between items-center mb-1.5"><span className="text-xs text-slate-400">전체 응답률</span><span className={`text-sm font-bold ${metrics.responseRateOverall >= 75 ? "text-emerald-600" : metrics.responseRateOverall >= 50 ? "text-amber-600" : "text-red-600"}`}>{Math.round(metrics.responseRateOverall)}%</span></div>
              <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden"><div className={`h-full rounded-full ${metrics.responseRateOverall >= 75 ? "bg-emerald-400" : metrics.responseRateOverall >= 50 ? "bg-amber-400" : "bg-red-400"}`} style={{ width: `${metrics.responseRateOverall}%` }} /></div>
              <p className="mt-2 text-[11px] text-slate-400">최근 7일 {Math.round(metrics.responseRateLast7d)}% · 연속 미응답 {metrics.currentConsecutiveNoResponse}일</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <h3 className="text-sm font-semibold text-[#1A2340] mb-3">처리 상태</h3>
            <div className="space-y-2 mb-4">
              {(["확인완료", "연락필요", "관찰지속"] as ActionStatus[]).map((status) => {
                const colors = {
                  확인완료: { active: "border-emerald-500 bg-emerald-50 text-emerald-700", dot: "bg-emerald-500" },
                  연락필요: { active: "border-red-400 bg-red-50 text-red-700", dot: "bg-red-500" },
                  관찰지속: { active: "border-amber-400 bg-amber-50 text-amber-700", dot: "bg-amber-500" },
                }[status];
                return (
                  <button key={status} onClick={() => { setProcessStatus(status); setSaved(false); }} className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border-2 text-sm font-medium transition-all ${processStatus === status ? colors.active : "border-slate-100 text-slate-500 hover:border-slate-200"}`}>
                    <span className={`w-3 h-3 rounded-full border-2 flex-shrink-0 ${processStatus === status ? `${colors.dot} border-transparent` : "border-slate-300"}`} />{status}
                  </button>
                );
              })}
            </div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">메모</label>
            <textarea value={memo} onChange={(event) => setMemo(event.target.value)} placeholder="확인 내용, 통화 기록 등을 남겨주세요" rows={3} className="w-full text-xs border border-slate-200 rounded-xl px-3 py-2 text-[#1A2340] placeholder-slate-300 resize-none focus:outline-none focus:border-[#3B6EBE] bg-slate-50" />
            <button onClick={saveAction} disabled={!processStatus || saving} className={`mt-2 w-full py-2 rounded-lg text-xs font-semibold transition-all disabled:bg-slate-300 ${saved ? "bg-emerald-500 text-white" : "bg-[#3B6EBE] text-white hover:bg-[#2E5BA8]"}`}>
              {saving ? "저장 중..." : saved ? "✓ 서버에 저장됨" : "저장"}
            </button>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <div className="flex items-center justify-between mb-4"><h3 className="text-sm font-semibold text-[#1A2340]">응답률 추이</h3><span className="text-xs text-slate-400">최근 7주</span></div>
            {trend.length ? (
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={trend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" /><XAxis dataKey="period" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} /><YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} /><Tooltip content={<CustomTooltip />} /><ReferenceLine y={70} stroke="#FCD34D" strokeDasharray="4 4" strokeWidth={1.5} /><Line type="monotone" dataKey="rate" stroke="#3B6EBE" strokeWidth={2.5} dot={{ fill: "#3B6EBE", r: 4, strokeWidth: 2, stroke: "white" }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <p className="py-12 text-center text-xs text-slate-400">표시할 응답 기록이 없습니다.</p>}
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded bg-[#3B6EBE] text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">AI</div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2"><h3 className="text-sm font-semibold text-[#1A2340]">판단 근거 상세</h3><span className="text-xs text-slate-400">{assessment.analyzer} · {assessment.analyzerVersion}</span></div>
                <div className="bg-slate-50 rounded-xl p-3 border border-slate-100"><p className="text-sm text-slate-700 leading-relaxed">{assessment.summary}</p>
                  {assessment.evidence.length > 0 && <ul className="mt-2 space-y-1">{assessment.evidence.map((item, index) => <li key={`${item.metric}-${index}`} className="text-xs text-slate-500">• {item.description}</li>)}</ul>}
                </div>
                <p className="text-xs text-[#3B6EBE] mt-2">※ 지원 공백 가능성 탐지를 위한 참고 자료입니다. 최종 판단은 전담요원이 합니다.</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <div className="flex items-center justify-between mb-4"><h3 className="text-sm font-semibold text-[#1A2340]">최근 응답 로그</h3><span className="text-xs text-slate-400">최근 {logs.length}건</span></div>
            {logs.length === 0 && <p className="py-8 text-center text-xs text-slate-400">응답 로그가 없습니다.</p>}
            <div className="space-y-3">
              {logs.map((log) => {
                const difficult = ["매우 힘듦", "많이 힘들어요", "힘듦", "좀 힘들어요"].includes(log.responseType ?? "");
                return (
                  <div key={log.checkinId} className={`rounded-xl border p-4 ${difficult ? "border-red-100 bg-red-50/40" : "border-slate-100 bg-slate-50/40"}`}>
                    <div className="flex items-center justify-between mb-2"><div className="flex items-center gap-2"><span className="text-base">{MOOD_CONFIG[log.responseType ?? ""] ?? "😐"}</span><span className={`text-xs font-semibold ${difficult ? "text-red-600" : "text-slate-600"}`}>{log.responseType ?? "응답"}</span></div><span className="text-xs text-slate-400">{log.date}</span></div>
                    {log.followUps.length > 0 && <div className="flex flex-wrap gap-1.5 mb-2">{log.followUps.map((item) => <span key={item} className="px-2 py-0.5 bg-[#6BA8A9]/10 text-[#3B6EBE] text-[11px] rounded-full">✓ {item}</span>)}</div>}
                    {log.responseText && <p className="text-xs text-slate-600 bg-white/70 rounded-lg px-3 py-2 border border-slate-100 leading-relaxed">“{log.responseText}”</p>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
