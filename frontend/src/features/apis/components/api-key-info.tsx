import type { ApiKey, LimitType } from "@/features/api-keys/schemas";
import { cn } from "@/lib/utils";
import {
	formatCompactNumber,
	formatCurrency,
	formatTimeLong,
} from "@/utils/formatters";

const LIMIT_TYPE_LABEL: Record<LimitType, string> = {
	total_tokens: "전체 토큰",
	input_tokens: "입력 토큰",
	output_tokens: "출력 토큰",
	cost_usd: "비용 (USD)",
	credits: "크레딧",
};

export type ApiKeyInfoProps = {
	apiKey: ApiKey;
	usageSummary?: ApiKey["usageSummary"] | null;
	usageMessage?: string | null;
	allowUsageSummaryFallback?: boolean;
};

function formatExpiry(value: string | null): string {
	if (!value) return "없음";
	const parsed = formatTimeLong(value);
	return `${parsed.date} ${parsed.time}`;
}

function isExpired(apiKey: ApiKey): boolean {
	if (!apiKey.expiresAt) return false;
	return new Date(apiKey.expiresAt).getTime() < Date.now();
}

export function ApiKeyInfo({
	apiKey,
	usageSummary,
	usageMessage,
	allowUsageSummaryFallback = true,
}: ApiKeyInfoProps) {
	const expired = isExpired(apiKey);
	const models = apiKey.allowedModels?.join(", ") || "전체 모델";
	const enforcedModel = apiKey.enforcedModel || null;
	const enforcedEffort = apiKey.enforcedReasoningEffort || null;
	const usage = allowUsageSummaryFallback
		? (usageSummary ?? apiKey.usageSummary)
		: (usageSummary ?? null);
	const hasUsage = usage && usage.requestCount > 0;

	return (
		<div className="space-y-4 rounded-lg border bg-muted/30 p-4">
			<h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
				키 상세
			</h3>
			<dl className="space-y-2 text-xs">
				<div className="flex items-center justify-between gap-2">
					<dt className="text-muted-foreground">접두사</dt>
					<dd className="font-mono font-medium">{apiKey.keyPrefix}</dd>
				</div>
				<div className="flex items-center justify-between gap-2">
					<dt className="text-muted-foreground">모델</dt>
					<dd className="text-right font-medium">{models}</dd>
				</div>
				{enforcedModel ? (
					<div className="flex items-center justify-between gap-2">
						<dt className="text-muted-foreground">강제 모델</dt>
						<dd className="font-mono font-medium">{enforcedModel}</dd>
					</div>
				) : null}
				{enforcedEffort ? (
					<div className="flex items-center justify-between gap-2">
						<dt className="text-muted-foreground">강제 추론 수준</dt>
						<dd className="font-medium">{enforcedEffort}</dd>
					</div>
				) : null}
				<div className="flex items-center justify-between gap-2">
					<dt className="text-muted-foreground">만료</dt>
					<dd
						className={cn(
							"font-medium",
							expired ? "text-red-600 dark:text-red-400" : "",
						)}
					>
						{expired ? "만료됨" : formatExpiry(apiKey.expiresAt)}
					</dd>
				</div>
				<div className="flex items-start justify-between gap-2">
					<dt className="text-muted-foreground">사용량</dt>
					<dd className="text-right tabular-nums">
						{hasUsage ? (
							<span>
								<span className="font-medium">
									{formatCompactNumber(usage.totalTokens)} tok
								</span>
								<span className="mx-1 text-muted-foreground/40">|</span>
								<span className="font-medium">
									{formatCompactNumber(usage.cachedInputTokens)} 캐시
								</span>
								<span className="mx-1 text-muted-foreground/40">|</span>
								<span className="font-medium">
									{formatCompactNumber(usage.requestCount)} 요청
								</span>
								<span className="mx-1 text-muted-foreground/40">|</span>
								<span className="font-medium">
									{formatCurrency(usage.totalCostUsd)}
								</span>
							</span>
						) : (
							<span className="text-muted-foreground">
								{usageMessage ?? "기록된 사용량이 없습니다"}
							</span>
						)}
					</dd>
				</div>
				<div className="space-y-1.5">
					<div className="flex items-center justify-between gap-2">
						<dt className="text-muted-foreground">제한</dt>
						<dd className="text-right tabular-nums">
							{apiKey.limits.length > 0 ? (
								<span className="font-medium">
									{apiKey.limits.length}개 설정됨
								</span>
							) : (
								<span className="text-muted-foreground">
									설정된 제한 없음
								</span>
							)}
						</dd>
					</div>
					{apiKey.limits.map((limit) => {
						const isCost = limit.limitType === "cost_usd";
						const percent =
							limit.maxValue > 0
								? Math.min(100, (limit.currentValue / limit.maxValue) * 100)
								: 0;
						const current = isCost
							? `$${(limit.currentValue / 1_000_000).toFixed(2)}`
							: formatCompactNumber(limit.currentValue);
						const max = isCost
							? `$${(limit.maxValue / 1_000_000).toFixed(2)}`
							: formatCompactNumber(limit.maxValue);
						const modelFilter = limit.modelFilter || "전체";

						return (
							<div key={limit.id} className="space-y-1 pl-2">
								<div className="flex items-center justify-between gap-2 text-xs tabular-nums">
									<span className="text-muted-foreground">
										{LIMIT_TYPE_LABEL[limit.limitType]} ({limit.limitWindow},{" "}
										{modelFilter})
									</span>
									<span className="font-medium">
										{current} / {max}
									</span>
								</div>
								<div className="h-1.5 w-full rounded-full bg-muted">
									<div
										className={cn(
											"h-full rounded-full transition-all",
											percent >= 90
												? "bg-red-500"
												: percent >= 70
													? "bg-orange-500"
													: "bg-primary",
										)}
										style={{ width: `${percent}%` }}
									/>
								</div>
							</div>
						);
					})}
				</div>
			</dl>
		</div>
	);
}
