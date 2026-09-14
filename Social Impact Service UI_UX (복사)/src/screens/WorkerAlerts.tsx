import { useEffect, useState } from "react";
import { api, errorMessage } from "../lib/api";
import type { AlertRecord, StatusLabel, YouthListItem } from "../types";

interface Props {
  onBack: () => void;
  onSelectYouth: (youthId: string) => void;
}

const STATUS_CONFIG: Record<StatusLabel, { bg: string; text: string; border: string; dot: string }> = {
  "정상": { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", dot: "bg-emerald-500" },
  "훼손 의심": { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", dot: "bg-red-500" },
  "관심 필요": { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", dot: "bg-amber-500" },
};

function dateTime(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function WorkerAlerts({ onBack, onSelectYouth }: Props) {
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [youths, setYouths] = useState<Record<string, YouthListItem>>({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [alertItems, youthItems] = await Promise.all([api.listAlerts(), api.listYouths()]);
      setAlerts(alertItems);
      setYouths(Object.fromEntries(youthItems.map((item) => [item.youthId, item])));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const acknowledge = async (alertId: string) => {
    setSavingId(alertId);
    setError("");
    try {
      const updated = await api.updateAlert(alertId, "확인완료");
      setAlerts((current) => current.map((item) => item.alertId === alertId ? updated : item));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSavingId(null);
    }
  };

  const newCount = alerts.filter((alert) => alert.status === "미확인").length;

  return (
    <div className="w-full max-w-[780px]">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-400 hover:text-[#3B6EBE] transition-colors">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 12L6 8L10 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            목록으로
          </button>
          <span className="text-slate-300">|</span>
          <h1 className="text-xl font-bold text-[#1A2340]">알림 목록</h1>
          <span className="px-2 py-0.5 bg-red-100 text-red-600 text-xs font-bold rounded-full">{newCount}건 신규</span>
        </div>
        <p className="text-xs text-slate-400">실시간 저장 데이터 기준</p>
      </div>

      <div className="flex items-start gap-3 bg-blue-50 border border-blue-100 rounded-2xl px-4 py-3 mb-5">
        <div className="w-5 h-5 rounded-full bg-[#3B6EBE] text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">AI</div>
        <p className="text-xs text-[#2E5BA8] leading-relaxed">
          아래 알림은 응답 패턴을 분석해 <strong>지원 공백 가능성</strong>을 탐지한 결과입니다.
          AI는 청년을 진단하거나 위험등급을 매기지 않습니다. <strong>최종 판단과 개입은 항상 전담요원이 합니다.</strong>
        </p>
      </div>

      {loading && <div className="bg-white rounded-2xl py-16 text-center text-sm text-slate-400">알림을 불러오는 중...</div>}
      {!loading && error && (
        <div role="alert" className="bg-white rounded-2xl py-12 text-center text-sm text-red-500">
          <p>{error}</p>
          <button onClick={load} className="mt-3 text-[#3B6EBE] font-semibold">다시 시도</button>
        </div>
      )}
      {!loading && !error && alerts.length === 0 && (
        <div className="bg-white rounded-2xl py-16 text-center text-sm text-slate-400">현재 생성된 알림이 없습니다.</div>
      )}

      <div className="space-y-4">
        {alerts.map((alert) => {
          const cfg = STATUS_CONFIG[alert.label];
          const youth = youths[alert.youthId];
          const isNew = alert.status === "미확인";
          const reason = [alert.summary, ...alert.evidence.map((item) => item.description)].join(" ");
          return (
            <div key={alert.alertId} className={`bg-white rounded-2xl border shadow-sm overflow-hidden ${isNew ? "ring-1 ring-red-200" : ""}`}>
              <div className={`px-5 py-4 border-b ${cfg.border} ${cfg.bg}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {isNew && <span className="px-2 py-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full tracking-wide">NEW</span>}
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#6BA8A9] to-[#3B6EBE] text-white text-sm font-bold flex items-center justify-center">
                      {youth?.name[0] ?? "?"}
                    </div>
                    <div>
                      <span className="font-bold text-[#1A2340] text-sm">{youth?.name ?? alert.youthId}</span>
                      <span className={`ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />{alert.label}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-400">{dateTime(alert.updatedAt)}</p>
                    <p className="text-xs text-slate-400">처리 상태: {alert.status}</p>
                  </div>
                </div>
              </div>

              <div className="px-5 py-4">
                <div className="flex items-start gap-2 mb-4">
                  <div className="w-5 h-5 rounded bg-[#3B6EBE]/10 text-[#3B6EBE] text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">AI</div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 mb-1">판단 근거 요약</p>
                    <p className="text-sm text-slate-700 leading-relaxed">{reason}</p>
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2">
                  <button onClick={() => onSelectYouth(alert.youthId)} className="px-4 py-2 text-xs font-semibold text-[#3B6EBE] border border-[#3B6EBE] rounded-lg hover:bg-[#3B6EBE] hover:text-white transition-all">상세 보기</button>
                  <button
                    onClick={() => acknowledge(alert.alertId)}
                    disabled={savingId === alert.alertId || alert.status === "확인완료"}
                    className="px-4 py-2 text-xs font-semibold text-white bg-[#3B6EBE] rounded-lg hover:bg-[#2E5BA8] transition-all shadow-sm disabled:bg-slate-300"
                  >
                    {savingId === alert.alertId ? "저장 중..." : alert.status === "확인완료" ? "확인 완료" : "확인 처리"}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
