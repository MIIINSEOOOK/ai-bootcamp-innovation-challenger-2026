export type StatusLabel = "정상" | "관심 필요" | "훼손 의심";
export type ActionStatus = "확인완료" | "연락필요" | "관찰지속";
export type AnalyzerName = "rule" | "ai" | "hybrid" | "rule-fallback";

export interface DemoUser {
  userId: string;
  name: string;
  role: "case_worker" | "youth";
  region: string;
  youthId: string | null;
}

export interface YouthListItem {
  youthId: string;
  name: string;
  age: number;
  region: string;
  status: StatusLabel;
  lastResponseAt: string | null;
  responseRate: number;
  hasAlert: boolean;
}

export interface YouthRecord {
  youthId: string;
  name: string;
  age: number;
  caseWorker: string;
  region: string;
  scenarioType: string;
  scenarioNote: string | null;
  completeSilence: boolean;
  backstory: string;
  independenceStatus: {
    careExitDate: string;
    housing: string;
    employmentEducation: string;
  };
}

export interface CheckinRecord {
  checkinId: string;
  youthId: string;
  date: string;
  sent: boolean;
  message: string | null;
  responded: boolean;
  responseTimeMinutes: number | null;
  responseType: string | null;
  responseText: string | null;
  followUps: string[];
  createdAt: string;
}

export interface MetricSnapshot {
  youthId: string;
  periodStart: string | null;
  periodEnd: string | null;
  sentCount: number;
  responseCount: number;
  responseRateOverall: number;
  responseRateLast7d: number;
  responseRatePrev7d: number;
  responseRateChange7d: number;
  maxConsecutiveNoResponse: number;
  currentConsecutiveNoResponse: number;
  averageResponseTimeMinutes: number | null;
  averageResponseTimeLast7d: number | null;
  averageResponseTimePrev7d: number | null;
  responseTimeChangeMinutes: number | null;
  recentMoodAverage: number | null;
  previousMoodAverage: number | null;
  moodChange: number | null;
  lastResponseAt: string | null;
  updatedAt: string;
}

export interface EvidenceItem {
  metric: string;
  description: string;
  value: number | string | null;
  previousValue: number | string | null;
}

export interface AssessmentRecord {
  assessmentId: string;
  youthId: string;
  label: StatusLabel;
  summary: string;
  evidence: EvidenceItem[];
  analyzer: AnalyzerName;
  analyzerVersion: string;
  promptVersion: string;
  needsReview: boolean;
  disagreement: boolean;
  ruleLabel: StatusLabel | null;
  aiLabel: StatusLabel | null;
  createdAt: string;
}

export interface AlertRecord {
  alertId: string;
  youthId: string;
  assessmentId: string;
  label: StatusLabel;
  summary: string;
  evidence: EvidenceItem[];
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface CaseActionRecord {
  actionId: string;
  youthId: string;
  status: ActionStatus;
  memo: string;
  caseWorker: string;
  createdAt: string;
}

export interface YouthDetail {
  youth: YouthRecord;
  metrics: MetricSnapshot;
  assessment: AssessmentRecord;
  checkins: CheckinRecord[];
  caseActions: CaseActionRecord[];
}

export interface LoginResponse {
  accessToken: string;
  tokenType: "bearer";
  user: DemoUser;
  demoMode: boolean;
}
