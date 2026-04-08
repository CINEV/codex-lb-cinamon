import { Ellipsis, KeyRound, Pencil, RefreshCw, Trash2 } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ApiKey, LimitRule, LimitType } from "@/features/api-keys/schemas";
import { formatCompactNumber, formatCurrency, formatTimeLong } from "@/utils/formatters";

function formatExpiry(value: string | null): string {
  if (!value) {
    return "없음";
  }
  const parsed = formatTimeLong(value);
  return `${parsed.date} ${parsed.time}`;
}

const LIMIT_TYPE_SHORT: Record<LimitType, string> = {
  total_tokens: "토큰",
  input_tokens: "입력",
  output_tokens: "출력",
  cost_usd: "비용",
  credits: "크레딧",
};

function formatLimitSummary(limits: LimitRule[]): string {
  if (limits.length === 0) return "-";
  return limits
    .map((l) => {
      const type = LIMIT_TYPE_SHORT[l.limitType];
      const isCost = l.limitType === "cost_usd";
      const isCredits = l.limitType === "credits";
      const current = isCost
        ? `$${(l.currentValue / 1_000_000).toFixed(2)}`
        : formatCompactNumber(l.currentValue);
      const max = isCost
        ? `$${(l.maxValue / 1_000_000).toFixed(2)}`
        : formatCompactNumber(l.maxValue);
      const suffix = isCost ? l.limitWindow : isCredits ? `${l.limitWindow}` : l.limitWindow;
      return `${type}: ${current}/${max} ${suffix}`;
    })
    .join(" | ");
}

function formatUsageSummary(
  requestCount: number,
  totalTokens: number,
  cachedInputTokens: number,
  totalCostUsd: number,
): string {
  const total = formatCompactNumber(totalTokens);
  const cached = formatCompactNumber(cachedInputTokens);
  const requests = formatCompactNumber(requestCount);
  const cost = formatCurrency(totalCostUsd);
  return `${total} tok | ${cached} 캐시 | ${requests} 요청 | ${cost}`;
}

function getUsageValue(apiKey: ApiKey): string {
  if (!apiKey.usageSummary) {
    return "사용량 없음";
  }

  return formatUsageSummary(
    apiKey.usageSummary.requestCount,
    apiKey.usageSummary.totalTokens,
    apiKey.usageSummary.cachedInputTokens,
    apiKey.usageSummary.totalCostUsd,
  );
}

function getLimitValue(apiKey: ApiKey): string {
  if (apiKey.limits.length === 0) {
    return "제한 없음";
  }

  return formatLimitSummary(apiKey.limits);
}

export type ApiKeyTableProps = {
  keys: ApiKey[];
  busy: boolean;
  onEdit: (apiKey: ApiKey) => void;
  onDelete: (apiKey: ApiKey) => void;
  onRegenerate: (apiKey: ApiKey) => void;
};

export function ApiKeyTable({ keys, busy, onEdit, onDelete, onRegenerate }: ApiKeyTableProps) {
  if (keys.length === 0) {
    return <EmptyState icon={KeyRound} title="생성된 API 키가 없습니다" />;
  }

  return (
    <div className="overflow-x-auto rounded-xl border">
    <Table className="table-fixed">
      <TableHeader>
        <TableRow>
          <TableHead className="w-[20%] min-w-[12rem] pl-4 text-[11px] uppercase tracking-wider text-muted-foreground/80">이름</TableHead>
          <TableHead className="w-[10%] min-w-[8rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">접두사</TableHead>
          <TableHead className="w-[9%] min-w-[6.5rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">모델</TableHead>
          <TableHead className="w-[26%] min-w-[17rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">사용량</TableHead>
          <TableHead className="w-[14%] min-w-[12rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">제한</TableHead>
          <TableHead className="w-[8%] min-w-[7rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">만료</TableHead>
          <TableHead className="w-[7%] min-w-[5.5rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">상태</TableHead>
          <TableHead className="w-[6%] min-w-[4.5rem] pr-4 text-right text-[11px] uppercase tracking-wider text-muted-foreground/80">작업</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {keys.map((apiKey) => {
          const models = apiKey.allowedModels?.join(", ") || "전체";

          return (
            <TableRow key={apiKey.id}>
              <TableCell className="pl-4 font-medium truncate">{apiKey.name}</TableCell>
              <TableCell className="truncate font-mono text-xs">{apiKey.keyPrefix}</TableCell>
              <TableCell className="truncate">{models}</TableCell>
              <TableCell className="text-xs tabular-nums leading-tight whitespace-normal">{getUsageValue(apiKey)}</TableCell>
              <TableCell className="text-xs tabular-nums leading-tight whitespace-normal">{getLimitValue(apiKey)}</TableCell>
              <TableCell className="truncate text-xs text-muted-foreground">{formatExpiry(apiKey.expiresAt)}</TableCell>
              <TableCell>
                <Badge className={apiKey.isActive ? "bg-emerald-500 text-white" : "bg-zinc-500 text-white"}>
                  {apiKey.isActive ? "활성" : "비활성"}
                </Badge>
              </TableCell>
              <TableCell className="pr-4 text-right">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button type="button" size="icon-sm" variant="ghost" disabled={busy}>
                      <Ellipsis className="size-4" />
                      <span className="sr-only">작업</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => onEdit(apiKey)}>
                      <Pencil className="size-4" />
                      수정
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onRegenerate(apiKey)}>
                      <RefreshCw className="size-4" />
                      재생성
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem variant="destructive" onClick={() => onDelete(apiKey)}>
                      <Trash2 className="size-4" />
                      삭제
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
    </div>
  );
}
