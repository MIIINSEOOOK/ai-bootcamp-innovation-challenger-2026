import { useState } from "react";
import { api } from "./lib/api";
import WorkerAlerts from "./screens/WorkerAlerts";
import WorkerDetail from "./screens/WorkerDetail";
import WorkerList from "./screens/WorkerList";
import WorkerLogin from "./screens/WorkerLogin";
import YouthCheckin from "./screens/YouthCheckin";
import YouthComplete from "./screens/YouthComplete";
import type { DemoUser } from "./types";

type View = "login" | "checkin" | "complete" | "admin-list" | "admin-alerts" | "admin-detail";

function Brand({ worker = false }: { worker?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className={`flex h-9 w-9 items-center justify-center rounded-xl text-white shadow-sm ${worker ? "bg-[#3B6EBE]" : "bg-[#6BA8A9]"}`}>
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
          <path d="M10 2C10 2 4 5 4 10.5C4 13.538 6.686 16 10 16C13.314 16 16 13.538 16 10.5C16 5 10 2 10 2Z" fill="white" opacity="0.9" />
          <circle cx="10" cy="10" r="2.5" fill="white" />
        </svg>
      </div>
      <div>
        <p className="text-[15px] font-bold leading-none text-[#1A2340]">자립동행</p>
        <p className="mt-1 text-[10px] text-slate-400">{worker ? "전담요원 관리 시스템" : "오늘의 안부"}</p>
      </div>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState<View>("login");
  const [user, setUser] = useState<DemoUser | null>(null);
  const [selectedYouthId, setSelectedYouthId] = useState("P02");

  const handleLogin = (nextUser: DemoUser) => {
    setUser(nextUser);
    setView(nextUser.role === "youth" ? "checkin" : "admin-list");
  };

  const logout = () => {
    api.logout();
    setUser(null);
    setSelectedYouthId("P02");
    setView("login");
  };

  if (view === "login" || !user) {
    return (
      <main className="flex min-h-full items-center justify-center bg-[radial-gradient(circle_at_top_left,#E8F4F4_0%,#F5F7FA_42%,#EDF2F8_100%)] px-4 py-10">
        <WorkerLogin onLogin={handleLogin} />
      </main>
    );
  }

  if (user.role === "youth") {
    return (
      <div className="min-h-full bg-[linear-gradient(160deg,#E8F4F4_0%,#FDF6EE_100%)]">
        <header className="border-b border-white/70 bg-white/75 backdrop-blur">
          <div className="mx-auto flex h-16 max-w-[980px] items-center justify-between px-5">
            <Brand />
            <div className="flex items-center gap-4">
              <div className="hidden text-right sm:block">
                <p className="text-xs font-semibold text-[#2C4A52]">{user.name} 님</p>
                <p className="mt-0.5 text-[10px] text-slate-400">안전하게 로그인됨</p>
              </div>
              <button onClick={logout} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-500 hover:border-[#6BA8A9] hover:text-[#5A9495]">로그아웃</button>
            </div>
          </div>
        </header>
        <main className="flex justify-center px-4 py-8 sm:py-12">
          {view === "checkin" && (
            <YouthCheckin
              youthId={user.youthId ?? "P02"}
              youthName={user.name}
              onSubmit={() => setView("complete")}
            />
          )}
          {view === "complete" && (
            <YouthComplete
              youthName={user.name}
              onBack={() => setView("checkin")}
              onLogout={logout}
            />
          )}
        </main>
      </div>
    );
  }

  const section = view === "admin-alerts" ? "alerts" : "youths";
  return (
    <div className="min-h-full bg-[#F5F7FA]">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 shadow-sm backdrop-blur">
        <div className="mx-auto flex h-[72px] max-w-[1180px] items-center justify-between px-5">
          <div className="flex h-full items-center gap-10">
            <Brand worker />
            <nav className="hidden h-full items-center gap-1 sm:flex" aria-label="관리자 메뉴">
              <button onClick={() => setView("admin-list")} className={`relative h-full px-4 text-sm font-semibold transition-colors ${section === "youths" ? "text-[#3B6EBE]" : "text-slate-400 hover:text-slate-600"}`}>
                담당 청년
                {section === "youths" && <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-[#3B6EBE]" />}
              </button>
              <button onClick={() => setView("admin-alerts")} className={`relative h-full px-4 text-sm font-semibold transition-colors ${section === "alerts" ? "text-[#3B6EBE]" : "text-slate-400 hover:text-slate-600"}`}>
                알림 센터
                <span className="absolute right-1 top-5 h-1.5 w-1.5 rounded-full bg-red-500" />
                {section === "alerts" && <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-[#3B6EBE]" />}
              </button>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right md:block">
              <p className="text-xs font-semibold text-[#1A2340]">{user.name}</p>
              <p className="mt-0.5 text-[10px] text-slate-400">{user.region}</p>
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#3B6EBE]/10 text-xs font-bold text-[#3B6EBE]">{user.name[0]}</div>
            <button onClick={logout} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-500 hover:border-[#3B6EBE] hover:text-[#3B6EBE]">로그아웃</button>
          </div>
        </div>
        <nav className="flex border-t border-slate-100 px-4 sm:hidden" aria-label="모바일 관리자 메뉴">
          <button onClick={() => setView("admin-list")} className={`flex-1 py-3 text-xs font-semibold ${section === "youths" ? "text-[#3B6EBE]" : "text-slate-400"}`}>담당 청년</button>
          <button onClick={() => setView("admin-alerts")} className={`flex-1 py-3 text-xs font-semibold ${section === "alerts" ? "text-[#3B6EBE]" : "text-slate-400"}`}>알림 센터</button>
        </nav>
      </header>

      <main className="mx-auto flex max-w-[1180px] justify-center px-4 py-7 sm:px-6 sm:py-9">
        {view === "admin-list" && (
          <WorkerList
            onSelectYouth={(youthId) => {
              setSelectedYouthId(youthId);
              setView("admin-detail");
            }}
            onAlerts={() => setView("admin-alerts")}
          />
        )}
        {view === "admin-alerts" && (
          <WorkerAlerts
            onBack={() => setView("admin-list")}
            onSelectYouth={(youthId) => {
              setSelectedYouthId(youthId);
              setView("admin-detail");
            }}
          />
        )}
        {view === "admin-detail" && (
          <WorkerDetail youthId={selectedYouthId} onBack={() => setView("admin-list")} />
        )}
      </main>
    </div>
  );
}
