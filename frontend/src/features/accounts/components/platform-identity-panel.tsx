import type { AccountSummary } from "@/features/accounts/schemas";
import {
  formatCompactNumber,
  formatCurrency,
  formatProviderLabel,
  formatRouteFamilyLabel,
  formatTimeLong,
} from "@/utils/formatters";

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "아직 검증되지 않음";
  }
  const formatted = formatTimeLong(value);
  if (formatted.date === "--") {
    return "아직 검증되지 않음";
  }
  return `${formatted.date} ${formatted.time}`;
}

function MetadataRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="space-y-1">
      <dt className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export type PlatformIdentityPanelProps = {
  account: AccountSummary;
};

export function PlatformIdentityPanel({ account }: PlatformIdentityPanelProps) {
  const requestUsage = account.requestUsage ?? null;
  const hasRequestUsage = (requestUsage?.requestCount ?? 0) > 0;
  const routeFamilies = account.eligibleRouteFamilies.length > 0
    ? account.eligibleRouteFamilies.map((routeFamily) => {
        if (routeFamily === "public_models_http") {
          return `Fallback ${formatRouteFamilyLabel(routeFamily)}`;
        }
        if (routeFamily === "public_responses_http") {
          return "Fallback stateless HTTP /v1/responses";
        }
        return formatRouteFamilyLabel(routeFamily);
      }).join(", ")
    : "None";
  const responsesFallbackEnabled = account.eligibleRouteFamilies.includes("public_responses_http");

  return (
    <div className="space-y-4 rounded-lg border bg-muted/30 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        OpenAI 플랫폼
      </h3>

      <dl className="grid gap-4 md:grid-cols-2">
        <MetadataRow label="공급자" value={`${formatProviderLabel(account.providerKind)} API 키`} />
        <MetadataRow label="라우팅 대상" value={account.routingSubjectId || "할당되지 않음"} />
        <MetadataRow label="허용된 폴백 라우트" value={routeFamilies} />
        <MetadataRow label="조직" value={account.organization || "기본값"} />
        <MetadataRow label="프로젝트" value={account.project || "기본값"} />
        <MetadataRow label="마지막 검증" value={formatTimestamp(account.lastValidatedAt)} />
        <MetadataRow label="마지막 인증 실패" value={account.lastAuthFailureReason || "없음"} />
      </dl>

      <div className="rounded-md border bg-background/60 px-3 py-2">
        <p className="text-xs text-muted-foreground">
          폴백 전용입니다. ChatGPT 계정이 항상 기본 경로로 유지되며, 이 키는 기본 또는 보조 사용량 임계치 때문에 호환 가능한 ChatGPT 풀이 비정상일 때만 사용됩니다.
        </p>
        {responsesFallbackEnabled ? (
          <p className="mt-1 text-xs text-muted-foreground">
            상태 없는 HTTP <code>/v1/responses</code> 전용입니다. Compact, chat completions, websocket, 연속성 의존 요청은 계속 ChatGPT에 남습니다.
          </p>
        ) : null}
      </div>

      <div className="rounded-md border bg-background/60 px-3 py-2">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          요청 로그 합계
        </p>
        {hasRequestUsage ? (
          <p className="mt-1 text-xs tabular-nums text-muted-foreground">
            {formatCompactNumber(requestUsage?.totalTokens)} tok |{" "}
            {formatCompactNumber(requestUsage?.cachedInputTokens)} cached |{" "}
            {formatCompactNumber(requestUsage?.requestCount)} req |{" "}
            {formatCurrency(requestUsage?.totalCostUsd)}
          </p>
        ) : (
          <p className="mt-1 text-xs text-muted-foreground">아직 요청 사용량이 없습니다.</p>
        )}
      </div>
    </div>
  );
}
