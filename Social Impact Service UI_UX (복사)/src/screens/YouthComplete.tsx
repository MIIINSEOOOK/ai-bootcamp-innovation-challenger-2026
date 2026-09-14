interface Props {
  youthName: string;
  onBack: () => void;
  onLogout: () => void;
}

export default function YouthComplete({ youthName, onBack, onLogout }: Props) {
  const time = new Intl.DateTimeFormat("ko-KR", { hour: "2-digit", minute: "2-digit" }).format(new Date());
  const displayName = youthName.endsWith("연") ? youthName.slice(-2) : youthName;

  return (
    <div className="w-full max-w-[430px]">
      <div className="flex min-h-[590px] flex-col items-center justify-center overflow-hidden rounded-3xl border border-white/80 bg-white/65 px-8 text-center shadow-xl backdrop-blur-sm">
        <div className="relative mb-8">
          <div className="flex h-32 w-32 items-center justify-center rounded-full bg-gradient-to-br from-white to-[#E8F4F4] text-6xl shadow-inner">🌱</div>
          <div className="absolute -right-1 -top-1 flex h-8 w-8 items-center justify-center rounded-full border-2 border-[#F4A261]/40 bg-[#F4A261]/20 text-base">✨</div>
          <div className="absolute -left-3 bottom-0 flex h-7 w-7 items-center justify-center rounded-full bg-[#6BA8A9]/20 text-sm">✓</div>
        </div>

        <p className="mb-2 text-xs font-bold tracking-[0.16em] text-[#6BA8A9]">CHECK-IN COMPLETE</p>
        <h2 className="mb-3 text-2xl font-bold leading-snug text-[#2C4A52]">오늘도 알려줘서<br />고마워요</h2>
        <p className="text-sm leading-6 text-[#5A8490]">{displayName} 씨의 오늘 안부가<br />담당 전담요원에게 잘 전달됐어요.</p>

        <div className="mt-8 w-full rounded-2xl border border-[#D4ECEC] bg-white/80 p-5 text-left">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">✓</span>
              <div><p className="text-xs font-semibold text-[#2C4A52]">오늘의 안부 제출 완료</p><p className="mt-1 text-[11px] text-[#8AABAF]">서버에 안전하게 저장되었습니다</p></div>
            </div>
            <span className="text-xs font-medium text-[#6BA8A9]">{time}</span>
          </div>
        </div>

        <p className="mt-5 text-xs leading-5 text-[#8AABAF]">내일도 같은 시간에 편하게 알려주세요.<br />응답하지 못하는 날이 있어도 괜찮아요.</p>

        <div className="mt-8 flex w-full gap-2">
          <button onClick={onBack} className="flex-1 rounded-xl border border-[#A8C5C6] bg-white px-4 py-3 text-sm font-semibold text-[#5A8490] hover:border-[#6BA8A9]">응답 수정</button>
          <button onClick={onLogout} className="flex-1 rounded-xl bg-[#6BA8A9] px-4 py-3 text-sm font-semibold text-white shadow-md shadow-[#6BA8A9]/20 hover:bg-[#5A9495]">마치기</button>
        </div>
      </div>
    </div>
  );
}
