import { Inbox } from "lucide-react";
import { useMemo, useState } from "react";

import { isEmailLabel } from "@/components/blur-email";
import { CopyButton } from "@/components/copy-button";
import { usePrivacyStore } from "@/hooks/use-privacy";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PaginationControls } from "@/features/dashboard/components/filters/pagination-controls";
import type { AccountSummary, RequestLog } from "@/features/dashboard/schemas";
import { REQUEST_STATUS_LABELS } from "@/utils/constants";
import {
  formatCompactNumber,
  formatCurrency,
  formatModelLabel,
  formatProviderLabel,
  formatSlug,
  formatTimeLong,
} from "@/utils/formatters";

const STATUS_CLASS_MAP: Record<string, string> = {
  ok: "bg-emerald-500/15 text-emerald-700 border-emerald-500/20 hover:bg-emerald-500/20 dark:text-emerald-400",
  rate_limit: "bg-orange-500/15 text-orange-700 border-orange-500/20 hover:bg-orange-500/20 dark:text-orange-400",
  quota: "bg-red-500/15 text-red-700 border-red-500/20 hover:bg-red-500/20 dark:text-red-400",
  error: "bg-zinc-500/15 text-zinc-700 border-zinc-500/20 hover:bg-zinc-500/20 dark:text-zinc-400",
};

const TRANSPORT_LABELS: Record<string, string> = {
  http: "HTTP",
  websocket: "WS",
};

const TRANSPORT_CLASS_MAP: Record<string, string> = {
  http: "bg-slate-500/10 text-slate-700 border-slate-500/20 hover:bg-slate-500/15 dark:text-slate-300",
  websocket: "bg-sky-500/15 text-sky-700 border-sky-500/20 hover:bg-sky-500/20 dark:text-sky-300",
};

function formatRouteClassLabel(value: string | null | undefined): string {
  switch (value) {
    case "chatgpt_private":
      return "ChatGPT 전용";
    case "openai_public_http":
      return "OpenAI 공개 HTTP";
    case "openai_public_ws":
      return "OpenAI 공개 WS";
    default:
      return value ? formatSlug(value) : "—";
  }
}

export type RecentRequestsTableProps = {
  requests: RequestLog[];
  accounts: AccountSummary[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
  onLimitChange: (limit: number) => void;
  onOffsetChange: (offset: number) => void;
};

export function RecentRequestsTable({
  requests,
  accounts,
  total,
  limit,
  offset,
  hasMore,
  onLimitChange,
  onOffsetChange,
}: RecentRequestsTableProps) {
  const [selectedRequest, setSelectedRequest] = useState<RequestLog | null>(null);
  const blurred = usePrivacyStore((s) => s.blurred);

  const accountLabelMap = useMemo(() => {
    const index = new Map<string, string>();
    for (const account of accounts) {
      index.set(account.accountId, account.displayName || account.email || account.accountId);
    }
    return index;
  }, [accounts]);

  /** Account IDs whose label is an email. */
  const emailLabelIds = useMemo(() => {
    const ids = new Set<string>();
    for (const account of accounts) {
      const label = account.displayName || account.email;
      if (isEmailLabel(label, account.email)) {
        ids.add(account.accountId);
      }
    }
    return ids;
  }, [accounts]);

  if (requests.length === 0) {
    return (
      <EmptyState
        icon={Inbox}
        title="요청 로그가 없습니다"
        description="현재 필터와 일치하는 요청 로그가 없습니다."
      />
    );
  }

  return (
    <div className="space-y-3">
    <div className="rounded-xl border bg-card">
      <div className="relative overflow-x-auto">
        <Table className="min-w-[1160px] table-fixed">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-28 pl-4 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">시간</TableHead>
              <TableHead className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">계정</TableHead>
              <TableHead className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">API 키</TableHead>
              <TableHead className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">모델</TableHead>
              <TableHead className="w-20 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">전송</TableHead>
              <TableHead className="w-24 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">상태</TableHead>
              <TableHead className="w-24 text-right text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">토큰</TableHead>
              <TableHead className="w-16 text-right text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">비용</TableHead>
              <TableHead className="w-72 pr-4 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">오류</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {requests.map((request) => {
              const time = formatTimeLong(request.requestedAt);
              const subjectId = request.accountId ?? request.routingSubjectId;
              const accountLabel = subjectId ? (accountLabelMap.get(subjectId) ?? subjectId) : "—";
              const isEmailLabel = !!(subjectId && emailLabelIds.has(subjectId));
              const providerMetadata = [
                request.providerKind ? formatProviderLabel(request.providerKind) : null,
                request.routingSubjectId,
              ].filter(Boolean).join(" | ");
              const errorPreview = request.errorMessage || request.rejectionReason || request.errorCode || "-";
              const hasError = !!(request.errorCode || request.errorMessage || request.rejectionReason);
              const visibleServiceTier = request.actualServiceTier ?? request.serviceTier;
              const showRequestedTier =
                !!request.requestedServiceTier && request.requestedServiceTier !== visibleServiceTier;

              return (
                <TableRow key={request.requestId}>
                  <TableCell className="pl-4 align-top">
                    <div className="leading-tight">
                      <div className="text-sm font-medium">{time.time}</div>
                      <div className="text-xs text-muted-foreground">{time.date}</div>
                    </div>
                  </TableCell>
                  <TableCell className="truncate align-top text-sm">
                    <div className="leading-tight">
                      <div>
                        {isEmailLabel && blurred ? (
                          <span className="privacy-blur">{accountLabel}</span>
                        ) : (
                          accountLabel
                        )}
                      </div>
                      {providerMetadata ? (
                        <div className="truncate text-[11px] text-muted-foreground">
                          {providerMetadata}
                        </div>
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell className="truncate align-top text-xs text-muted-foreground">
                    <div className="leading-tight">
                      <div>{request.apiKeyName || "--"}</div>
                      {request.upstreamRequestId ? (
                        <div className="truncate text-[11px]">업스트림 {request.upstreamRequestId}</div>
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell className="truncate align-top">
                    <div className="leading-tight">
                      <span className="font-mono text-xs">
                        {formatModelLabel(request.model, request.reasoningEffort, visibleServiceTier)}
                      </span>
                      {request.routeClass ? (
                        <div className="text-[11px] text-muted-foreground">
                          {formatRouteClassLabel(request.routeClass)}
                        </div>
                      ) : null}
                      {showRequestedTier ? (
                        <div className="text-[11px] text-muted-foreground">
                          요청됨 {request.requestedServiceTier}
                        </div>
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell className="align-top">
                    {request.transport ? (
                      <Badge
                        variant="outline"
                        className={TRANSPORT_CLASS_MAP[request.transport] ?? TRANSPORT_CLASS_MAP.http}
                      >
                        {TRANSPORT_LABELS[request.transport] ?? request.transport}
                      </Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground">--</span>
                    )}
                  </TableCell>
                  <TableCell className="align-top">
                    <Badge
                      variant="outline"
                      className={STATUS_CLASS_MAP[request.status] ?? STATUS_CLASS_MAP.error}
                    >
                      {REQUEST_STATUS_LABELS[request.status] ?? request.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right align-top font-mono text-xs tabular-nums">
                    <div className="leading-tight">
                      <div>{formatCompactNumber(request.tokens)}</div>
                      {request.cachedInputTokens != null && request.cachedInputTokens > 0 && (
                        <div className="text-[11px] text-muted-foreground">
                          {formatCompactNumber(request.cachedInputTokens)} 캐시됨
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right align-top font-mono text-xs tabular-nums">
                    {formatCurrency(request.costUsd)}
                  </TableCell>
                  <TableCell className="pr-4 align-top whitespace-normal">
                    {hasError ? (
                      <div className="space-y-2">
                        {request.errorCode ? (
                          <div>
                            <Badge variant="outline" className="max-w-full font-mono text-[10px]">
                              <span className="truncate">{request.errorCode}</span>
                            </Badge>
                          </div>
                        ) : null}
                        <p className="line-clamp-2 break-words text-xs leading-relaxed text-muted-foreground">
                          {errorPreview}
                        </p>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-[11px]"
                          onClick={() => setSelectedRequest(request)}
                        >
                          상세 보기
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>

      <div className="flex justify-end">
        <PaginationControls
          total={total}
          limit={limit}
          offset={offset}
          hasMore={hasMore}
          onLimitChange={onLimitChange}
          onOffsetChange={onOffsetChange}
        />
      </div>

      <Dialog open={selectedRequest !== null} onOpenChange={(open) => { if (!open) setSelectedRequest(null); }}>
        <DialogContent className="max-h-[85vh] sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>요청 상세</DialogTitle>
            <DialogDescription>요청 메타데이터를 확인하고 필요한 필드를 복사하세요.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 overflow-y-auto">
            <div className="space-y-3 rounded-md border bg-muted/30 p-4">
              <RequestDetailField
                label="요청 ID"
                value={selectedRequest?.requestId ?? "—"}
                mono
                copyValue={selectedRequest?.requestId ?? ""}
                copyLabel="요청 ID 복사"
                compactCopy
              />
              <div className="grid gap-3 sm:grid-cols-3">
                <RequestDetailField label="상태" value={selectedRequest ? (REQUEST_STATUS_LABELS[selectedRequest.status] ?? selectedRequest.status) : "—"} />
                <RequestDetailField label="모델" value={selectedRequest ? formatModelLabel(selectedRequest.model, selectedRequest.reasoningEffort, selectedRequest.actualServiceTier ?? selectedRequest.serviceTier) : "—"} mono />
                <RequestDetailField label="공급자" value={selectedRequest?.providerKind ? formatProviderLabel(selectedRequest.providerKind) : "—"} />
                <RequestDetailField label="라우팅 대상" value={selectedRequest?.routingSubjectId ?? "—"} mono />
                <RequestDetailField label="라우트 종류" value={formatRouteClassLabel(selectedRequest?.routeClass)} />
                <RequestDetailField label="전송" value={selectedRequest?.transport ? (TRANSPORT_LABELS[selectedRequest.transport] ?? selectedRequest.transport) : "—"} />
                <RequestDetailField label="시간" value={selectedRequest ? `${formatTimeLong(selectedRequest.requestedAt).time} ${formatTimeLong(selectedRequest.requestedAt).date}` : "—"} />
                <RequestDetailField label="오류 코드" value={selectedRequest?.errorCode ?? "—"} mono />
                <RequestDetailField
                  label="업스트림 요청 ID"
                  value={selectedRequest?.upstreamRequestId ?? "—"}
                  mono
                  copyValue={selectedRequest?.upstreamRequestId ?? undefined}
                  copyLabel="업스트림 요청 ID 복사"
                />
                <RequestDetailField label="거부 사유" value={selectedRequest?.rejectionReason ?? "—"} mono />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium">전체 오류</h3>
                {selectedRequest?.errorMessage ? (
                  <CopyButton value={selectedRequest.errorMessage} label="오류 복사" iconOnly />
                ) : null}
              </div>
              <div className="max-h-[36vh] overflow-y-auto rounded-md bg-muted/50 p-3">
                <p className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed">
                  {selectedRequest?.errorMessage ?? selectedRequest?.rejectionReason ?? selectedRequest?.errorCode ?? "기록된 오류 상세가 없습니다."}
                </p>
              </div>
            </div>
          </div>
          <DialogFooter showCloseButton />
        </DialogContent>
      </Dialog>
    </div>
  );
}

type RequestDetailFieldProps = {
  label: string;
  value: string;
  mono?: boolean;
  copyValue?: string;
  copyLabel?: string;
  compactCopy?: boolean;
};

function RequestDetailField({
  label,
  value,
  mono = false,
  copyValue,
  copyLabel = "복사",
  compactCopy = false,
}: RequestDetailFieldProps) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">
          {label}
        </div>
        {copyValue ? (
          <CopyButton value={copyValue} label={copyLabel} iconOnly={compactCopy} />
        ) : null}
      </div>
      <div className="flex flex-col items-start gap-2">
        <p className={`min-w-0 flex-1 break-all text-sm leading-relaxed ${mono ? "font-mono" : ""}`}>
          {value}
        </p>
      </div>
    </div>
  );
}
