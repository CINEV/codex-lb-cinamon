export const STATUS_LABELS = {
  active: "활성",
  paused: "일시 중지",
  limited: "속도 제한",
  exceeded: "할당량 초과",
  deactivated: "비활성화",
} as const;

export const ERROR_LABELS = {
  rate_limit: "속도 제한",
  quota: "할당량",
  timeout: "시간 초과",
  upstream: "업스트림",
  rate_limit_exceeded: "속도 제한",
  usage_limit_reached: "할당량",
  insufficient_quota: "할당량",
  usage_not_included: "할당량",
  quota_exceeded: "할당량",
  upstream_error: "업스트림",
} as const;

export const ROUTING_LABELS = {
  usage_weighted: "사용량 가중치",
  round_robin: "라운드 로빈",
  capacity_weighted: "용량 가중치",
  sticky: "고정",
} as const;

export const KNOWN_PLAN_TYPES = new Set([
  "free",
  "plus",
  "pro",
  "team",
  "business",
  "enterprise",
  "edu",
]);

export const DONUT_COLORS_LIGHT = [
  "#3b82f6",
  "#8b5cf6",
  "#10b981",
  "#f59e0b",
  "#ec4899",
  "#06b6d4",
] as const;

export const DONUT_COLORS_DARK = [
  "#2563eb",
  "#7c3aed",
  "#059669",
  "#d97706",
  "#db2777",
  "#0891b2",
] as const;

export const DONUT_COLORS = DONUT_COLORS_LIGHT;

export const MESSAGE_TONE_META = {
  success: {
    label: "성공",
    className: "active",
    defaultTitle: "가져오기 완료",
  },
  error: {
    label: "오류",
    className: "deactivated",
    defaultTitle: "가져오기 실패",
  },
  warning: {
    label: "경고",
    className: "limited",
    defaultTitle: "주의",
  },
  info: {
    label: "정보",
    className: "limited",
    defaultTitle: "메시지",
  },
  question: {
    label: "질문",
    className: "limited",
    defaultTitle: "확인",
  },
} as const;

export const REQUEST_STATUS_LABELS: Record<string, string> = {
  ok: "OK",
  rate_limit: "속도 제한",
  quota: "할당량",
  error: "오류",
};

export const RESET_ERROR_LABEL = "--";
