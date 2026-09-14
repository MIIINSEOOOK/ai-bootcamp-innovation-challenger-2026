import { useState } from "react";
import { api, errorMessage } from "../lib/api";

interface Props {
  youthId: string;
  youthName: string;
  onSubmit: () => void;
}

const QUICK_OPTIONS = [
  { emoji: "😊", label: "좋아요" },
  { emoji: "😐", label: "그냥 그래요" },
  { emoji: "😔", label: "좀 힘들어요" },
  { emoji: "😞", label: "많이 힘들어요" },
];

const FOLLOW_UPS = [
  "밥은 잘 챙겨 먹고 있어요",
  "잠을 충분히 자고 있어요",
  "오늘 밖에 나갔어요",
  "누군가와 이야기 나눴어요",
];

export default function YouthCheckin({ youthId, youthName, onSubmit }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [checks, setChecks] = useState<boolean[]>([false, false, false, false]);
  const [memo, setMemo] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const toggleCheck = (i: number) => {
    setChecks((prev) => prev.map((v, idx) => (idx === i ? !v : v)));
  };

  const canSubmit = selected !== null && !saving;
  const todayLabel = new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());
  const displayName = youthName.endsWith("연") ? `${youthName.slice(-2)}` : youthName;

  const handleSubmit = async () => {
    if (selected === null) return;
    setSaving(true);
    setError("");
    try {
      await api.submitCheckin({
        youthId,
        responseType: QUICK_OPTIONS[selected].label,
        responseText: memo.trim() || null,
        followUps: FOLLOW_UPS.filter((_, index) => checks[index]),
      });
      onSubmit();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="w-full max-w-[390px]">
      {/* Status bar area */}
      <div
        className="rounded-3xl overflow-hidden shadow-xl"
        style={{ background: "linear-gradient(160deg, #E8F4F4 0%, #FDF6EE 100%)" }}
      >
        {/* Header */}
        <div className="px-6 pt-8 pb-4">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs font-medium text-[#6BA8A9] tracking-wide">{todayLabel}</p>
              <h1 className="text-2xl font-bold text-[#2C4A52] mt-1 leading-tight">
                안녕하세요,<br />{displayName} 씨 👋
              </h1>
            </div>
            <div className="w-12 h-12 rounded-full bg-white/70 flex items-center justify-center shadow-sm text-2xl">
              🌿
            </div>
          </div>

          {/* Greeting card */}
          <div className="bg-white/80 backdrop-blur rounded-2xl p-4 mb-2 border border-[#D4ECEC]">
            <p className="text-sm text-[#4A6B73] leading-relaxed">
              오늘 하루는 어떠셨나요?<br />
              <span className="font-medium text-[#2C4A52]">짧게 알려주시면 충분해요.</span>
            </p>
            <p className="text-xs text-[#8AABAF] mt-2">
              ✦ 이 응답은 담당 전담요원에게 안전하게 전달됩니다
            </p>
          </div>
        </div>

        {/* Question area */}
        <div className="px-6 pb-6">
          {/* Main mood question */}
          <div className="mb-5">
            <p className="text-sm font-semibold text-[#2C4A52] mb-3">
              오늘 전반적인 기분은 어떤가요?
            </p>
            <div className="grid grid-cols-4 gap-2">
              {QUICK_OPTIONS.map((opt, i) => (
                <button
                  key={i}
                  onClick={() => setSelected(i)}
                  className={`flex flex-col items-center gap-1.5 py-3 rounded-2xl border-2 transition-all ${
                    selected === i
                      ? "border-[#6BA8A9] bg-[#6BA8A9]/10 shadow-md scale-105"
                      : "border-transparent bg-white/60 hover:bg-white/90"
                  }`}
                >
                  <span className="text-2xl">{opt.emoji}</span>
                  <span className="text-[10px] font-medium text-[#4A6B73] text-center leading-tight">
                    {opt.label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Follow-up checkboxes */}
          <div className="mb-5">
            <p className="text-sm font-semibold text-[#2C4A52] mb-3">
              오늘 해당하는 것이 있으면 체크해 주세요
            </p>
            <div className="space-y-2">
              {FOLLOW_UPS.map((item, i) => (
                <button
                  key={i}
                  onClick={() => toggleCheck(i)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all text-left ${
                    checks[i]
                      ? "border-[#6BA8A9] bg-[#6BA8A9]/10"
                      : "border-[#D4E8E8] bg-white/50 hover:bg-white/80"
                  }`}
                >
                  <div
                    className={`w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-all ${
                      checks[i]
                        ? "border-[#6BA8A9] bg-[#6BA8A9]"
                        : "border-[#A8C5C6]"
                    }`}
                  >
                    {checks[i] && (
                      <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                        <path
                          d="M1 4L3.8 7L9 1"
                          stroke="white"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </div>
                  <span className="text-sm text-[#4A6B73]">{item}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Free text */}
          <div className="mb-6">
            <p className="text-sm font-semibold text-[#2C4A52] mb-2">
              하고 싶은 말이 있으면 남겨주세요 <span className="font-normal text-[#8AABAF]">(선택)</span>
            </p>
            <textarea
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="어떤 이야기든 괜찮아요. 오늘의 작은 일들도 좋아요 :)"
              rows={3}
              className="w-full bg-white/70 border border-[#D4E8E8] rounded-2xl px-4 py-3 text-sm text-[#4A6B73] placeholder-[#A8C5C6] resize-none focus:outline-none focus:border-[#6BA8A9] focus:bg-white transition-all"
            />
          </div>

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={`w-full py-4 rounded-2xl font-semibold text-sm transition-all ${
              canSubmit
                ? "bg-[#6BA8A9] text-white shadow-lg shadow-[#6BA8A9]/30 hover:bg-[#5A9495] active:scale-98"
                : "bg-[#D4E8E8] text-[#A8C5C6] cursor-not-allowed"
            }`}
          >
            {saving ? "안부를 전송하는 중..." : "오늘의 안부 전하기"}
          </button>
          {error && (
            <p role="alert" className="text-center text-xs text-red-600 mt-2">
              {error}
            </p>
          )}
          {!canSubmit && (
            <p className="text-center text-xs text-[#A8C5C6] mt-2">
              기분을 선택하면 전송할 수 있어요
            </p>
          )}
        </div>
      </div>

      {/* Bottom note */}
      <p className="text-center text-xs text-slate-400 mt-4 px-4">
        응답 내용은 담당 요원에게만 전달됩니다 · 응답하지 않아도 괜찮아요
      </p>
    </div>
  );
}
