import { useState } from "react";
import { api, errorMessage } from "../lib/api";
import type { DemoUser } from "../types";

type LoginRole = "youth" | "case_worker";

interface Props {
  onLogin: (user: DemoUser) => void;
}

const ROLE_COPY = {
  youth: {
    title: "청년 로그인",
    description: "오늘의 안부를 편안하게 알려주세요.",
    username: "lee.seoyeon",
    label: "청년",
  },
  case_worker: {
    title: "전담요원 로그인",
    description: "담당 청년의 안부와 지원 공백을 확인하세요.",
    username: "kim.jiyeon",
    label: "전담요원",
  },
} as const;

function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className={`flex ${compact ? "h-10 w-10" : "h-11 w-11"} items-center justify-center rounded-xl bg-white/15 ring-1 ring-white/25`}>
        <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
          <path d="M10 2C10 2 4 5 4 10.5C4 13.538 6.686 16 10 16C13.314 16 16 13.538 16 10.5C16 5 10 2 10 2Z" fill="white" opacity="0.9" />
          <circle cx="10" cy="10" r="2.5" fill="white" />
        </svg>
      </div>
      <div><p className="text-lg font-bold">자립동행</p><p className="text-xs opacity-65">일상을 잇는 안전망</p></div>
    </div>
  );
}

export default function WorkerLogin({ onLogin }: Props) {
  const [role, setRole] = useState<LoginRole>("youth");
  const [id, setId] = useState<string>(ROLE_COPY.youth.username);
  const [pw, setPw] = useState("demo");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectRole = (nextRole: LoginRole) => {
    setRole(nextRole);
    setId(ROLE_COPY[nextRole].username);
    setError("");
  };

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await api.login(id, pw, role);
      onLogin(result.user);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-[920px] overflow-hidden rounded-[28px] bg-white shadow-2xl shadow-slate-900/10 ring-1 ring-slate-200/70 md:grid md:grid-cols-5">
      <section className="relative hidden min-h-[620px] overflow-hidden bg-gradient-to-br from-[#244E8A] via-[#3B6EBE] to-[#5A9698] p-10 text-white md:col-span-2 md:flex md:flex-col md:justify-between">
        <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-white/10" />
        <div className="absolute -bottom-24 -left-20 h-72 w-72 rounded-full bg-[#8ED1B2]/20" />
        <div className="relative">
          <Logo />
          <h1 className="mt-14 text-3xl font-bold leading-snug">작은 안부가<br />든든한 연결이 됩니다.</h1>
          <p className="mt-5 text-sm leading-7 text-white/70">매일의 짧은 응답을 통해 변화의 신호를 살피고, 필요한 순간 전담요원과 연결합니다.</p>
        </div>
        <div className="relative rounded-2xl border border-white/15 bg-white/10 p-5 backdrop-blur-sm">
          <p className="text-xs font-semibold text-[#D9F3E7]">안심하고 이용하세요</p>
          <p className="mt-2 text-xs leading-5 text-white/65">응답 내용은 담당 전담요원에게만 전달되며, 분석 결과는 지원을 위한 참고 자료로만 사용됩니다.</p>
        </div>
      </section>

      <section className="px-6 py-8 sm:px-10 sm:py-10 md:col-span-3 md:px-14 md:py-14">
        <div className="mb-8 rounded-2xl bg-gradient-to-r from-[#3B6EBE] to-[#6BA8A9] p-4 text-white md:hidden">
          <Logo compact />
        </div>
        <div className="mb-8">
          <p className="mb-2 text-xs font-bold tracking-[0.18em] text-[#3B6EBE]">WELCOME</p>
          <h2 className="text-2xl font-bold text-[#1A2340]">{ROLE_COPY[role].title}</h2>
          <p className="mt-2 text-sm text-slate-400">{ROLE_COPY[role].description}</p>
        </div>

        <div className="mb-7 grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1.5" role="tablist" aria-label="로그인 유형">
          {(["youth", "case_worker"] as LoginRole[]).map((item) => (
            <button
              key={item}
              type="button"
              role="tab"
              aria-selected={role === item}
              onClick={() => selectRole(item)}
              className={`rounded-lg px-3 py-2.5 text-sm font-semibold transition-all ${role === item ? "bg-white text-[#1A2340] shadow-sm" : "text-slate-400 hover:text-slate-600"}`}
            >
              {ROLE_COPY[item].label}
            </button>
          ))}
        </div>

        <form onSubmit={handleLogin}>
          <div className="space-y-4">
            <div>
              <label htmlFor="login-id" className="mb-1.5 block text-xs font-semibold text-slate-500">아이디</label>
              <input id="login-id" autoComplete="username" value={id} onChange={(event) => setId(event.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-[#1A2340] outline-none transition-all focus:border-[#3B6EBE] focus:bg-white focus:ring-2 focus:ring-[#3B6EBE]/10" />
            </div>
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label htmlFor="login-password" className="text-xs font-semibold text-slate-500">비밀번호</label>
                <span className="text-[11px] text-slate-400">데모 비밀번호: demo</span>
              </div>
              <input id="login-password" type="password" autoComplete="current-password" value={pw} onChange={(event) => setPw(event.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-[#1A2340] outline-none transition-all focus:border-[#3B6EBE] focus:bg-white focus:ring-2 focus:ring-[#3B6EBE]/10" />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !id.trim() || !pw}
            className={`mt-7 flex w-full items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-semibold text-white shadow-lg transition-all disabled:opacity-60 ${role === "youth" ? "bg-[#6BA8A9] shadow-[#6BA8A9]/20 hover:bg-[#5A9495]" : "bg-[#3B6EBE] shadow-[#3B6EBE]/20 hover:bg-[#2E5BA8]"}`}
          >
            {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />}
            {loading ? "로그인 중..." : `${ROLE_COPY[role].label}으로 시작하기`}
          </button>
          {error && <p role="alert" className="mt-3 text-center text-xs text-red-600">{error}</p>}
        </form>

        <div className="mt-8 border-t border-slate-100 pt-5 text-center">
          <p className="text-[11px] leading-5 text-slate-400">현재는 로컬 시연용 데모 계정입니다.<br />실제 인증 서비스는 동일한 로그인 화면에 연결할 수 있습니다.</p>
        </div>
      </section>
    </div>
  );
}
