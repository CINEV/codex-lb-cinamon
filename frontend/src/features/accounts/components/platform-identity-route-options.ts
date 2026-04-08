import type { PlatformRouteFamily } from "@/features/accounts/schemas";

export type CheckedState = boolean | "indeterminate";

export const PLATFORM_ROUTE_FAMILY_ORDER: PlatformRouteFamily[] = [
  "public_models_http",
  "public_responses_http",
];

export const PLATFORM_ROUTE_OPTIONS: Array<{
  value: PlatformRouteFamily;
  label: string;
  description: string;
}> = [
  {
    value: "public_models_http",
    label: "/v1/models",
    description: "이 ID가 공개 모델 조회 요청을 대체 처리하도록 허용합니다.",
  },
  {
    value: "public_responses_http",
    label: "/v1/responses",
    description: "이 ID가 상태 없는 HTTP Responses API 호출만 처리하도록 허용합니다.",
  },
];

export function shouldIncludeRouteFamily(checked: CheckedState): boolean {
  return checked === true;
}
