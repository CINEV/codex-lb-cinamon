import { useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ExpiryPicker } from "@/features/api-keys/components/expiry-picker";
import { LimitRulesEditor } from "@/features/api-keys/components/limit-rules-editor";
import { AccountMultiSelect } from "@/features/api-keys/components/account-multi-select";
import { ModelMultiSelect } from "@/features/api-keys/components/model-multi-select";
import type { ApiKey, ApiKeyUpdateRequest, LimitRuleCreate, LimitType, ServiceTierType } from "@/features/api-keys/schemas";
import { parseDate } from "@/utils/formatters";

import { hasLimitRuleChanges, normalizeLimitRules } from "./limit-rules-utils";

const formSchema = z.object({
  name: z.string().min(1, "이름은 필수입니다"),
  isActive: z.boolean(),
});

type FormValues = z.infer<typeof formSchema>;

export type ApiKeyEditDialogProps = {
  open: boolean;
  busy: boolean;
  apiKey: ApiKey | null;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: ApiKeyUpdateRequest) => Promise<void>;
};

type ApiKeyEditFormProps = {
  apiKey: ApiKey;
  busy: boolean;
  onSubmit: (payload: ApiKeyUpdateRequest) => Promise<void>;
  onClose: () => void;
};

function limitsToCreateRules(apiKey: ApiKey): LimitRuleCreate[] {
  return apiKey.limits.map((l) => ({
    limitType: l.limitType,
    limitWindow: l.limitWindow,
    maxValue: l.maxValue,
    modelFilter: l.modelFilter,
  }));
}

function hasSelectionChange(initialIds: string[], nextIds: string[]): boolean {
  if (initialIds.length !== nextIds.length) {
    return true;
  }

  const initialIdSet = new Set(initialIds);
  return nextIds.some((accountId) => !initialIdSet.has(accountId));
}

function ApiKeyEditForm({ apiKey, busy, onSubmit, onClose }: ApiKeyEditFormProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: apiKey.name,
      isActive: apiKey.isActive,
    },
  });

  const [selectedModels, setSelectedModels] = useState<string[]>(apiKey.allowedModels || []);
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>(apiKey.assignedAccountIds);
  const initialLimitRules = useMemo(() => limitsToCreateRules(apiKey), [apiKey]);
  const [limitRules, setLimitRules] = useState<LimitRuleCreate[]>(() => initialLimitRules);
  const [expiresAt, setExpiresAt] = useState<Date | null>(() => parseDate(apiKey.expiresAt));
  const [enforcedModel, setEnforcedModel] = useState<string>(apiKey.enforcedModel || "");
  const [enforcedReasoningEffort, setEnforcedReasoningEffort] = useState<string>(
    apiKey.enforcedReasoningEffort || "none",
  );
  const [enforcedServiceTier, setEnforcedServiceTier] = useState<string>(
    apiKey.enforcedServiceTier || "none",
  );

  const handleSubmit = async (values: FormValues) => {
    const normalizedLimits = normalizeLimitRules(limitRules);
    const shouldSubmitAssignedAccountIds =
      hasSelectionChange(apiKey.assignedAccountIds, selectedAccountIds) ||
      (apiKey.accountAssignmentScopeEnabled && selectedAccountIds.length === 0);
    const payload: ApiKeyUpdateRequest = {
      name: values.name,
      allowedModels: selectedModels.length > 0 ? selectedModels : null,
      enforcedModel: enforcedModel.trim() ? enforcedModel.trim() : null,
      enforcedReasoningEffort: enforcedReasoningEffort === "none" ? null : enforcedReasoningEffort as "minimal" | "low" | "medium" | "high" | "xhigh",
      enforcedServiceTier: enforcedServiceTier === "none" ? null : enforcedServiceTier as ServiceTierType,
      expiresAt: expiresAt?.toISOString() ?? null,
      isActive: values.isActive,
    };
    if (shouldSubmitAssignedAccountIds) {
      payload.assignedAccountIds = selectedAccountIds;
    }
    if (hasLimitRuleChanges(initialLimitRules, limitRules)) {
      payload.limits = normalizedLimits;
    }
    try {
      await onSubmit(payload);
    } catch {
      return;
    }
    onClose();
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)}>
        <div className="grid gap-x-6 sm:grid-cols-2">
          {/* Left column — General */}
          <div className="max-h-[55vh] space-y-3 overflow-y-auto overscroll-contain pl-1 pr-2">
            <h4 className="sticky top-0 bg-background pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">일반</h4>

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>이름</FormLabel>
                  <FormControl>
                    <Input {...field} autoComplete="off" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="space-y-1">
              <div className="text-sm font-medium">허용 모델</div>
              <ModelMultiSelect value={selectedModels} onChange={setSelectedModels} />
            </div>

            <div className="space-y-1">
              <div className="text-sm font-medium">할당 계정</div>
              <AccountMultiSelect value={selectedAccountIds} onChange={setSelectedAccountIds} />
            </div>

            <div className="space-y-1">
              <div className="text-sm font-medium">강제 모델</div>
              <Input
                value={enforcedModel}
                onChange={(e) => setEnforcedModel(e.target.value)}
                placeholder="예: gpt-5.3-codex"
                autoComplete="off"
              />
            </div>

            <div className="space-y-1">
              <div className="text-sm font-medium">강제 추론 수준</div>
              <Select value={enforcedReasoningEffort} onValueChange={setEnforcedReasoningEffort}>
                <SelectTrigger>
                  <SelectValue placeholder="없음" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">없음</SelectItem>
                  <SelectItem value="minimal">최소</SelectItem>
                  <SelectItem value="low">낮음</SelectItem>
                  <SelectItem value="medium">중간</SelectItem>
                  <SelectItem value="high">높음</SelectItem>
                  <SelectItem value="xhigh">매우 높음</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <div className="text-sm font-medium">강제 서비스 티어</div>
              <Select value={enforcedServiceTier} onValueChange={setEnforcedServiceTier}>
                <SelectTrigger>
                  <SelectValue placeholder="없음" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">없음</SelectItem>
                  <SelectItem value="auto">자동</SelectItem>
                  <SelectItem value="default">기본값</SelectItem>
                  <SelectItem value="priority">우선</SelectItem>
                  <SelectItem value="flex">Flex</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <div className="text-sm font-medium">만료</div>
              <ExpiryPicker value={expiresAt} onChange={setExpiresAt} />
            </div>

            <FormField
              control={form.control}
              name="isActive"
              render={({ field }) => (
                <div className="flex items-center justify-between rounded-md border p-2">
                  <span className="text-sm">활성</span>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </div>
              )}
            />
          </div>

          {/* Right column — Limits */}
          <div className="max-h-[55vh] space-y-3 overflow-y-auto overscroll-contain pl-1 pr-2 max-sm:mt-3 max-sm:border-t max-sm:pt-3">
            <h4 className="sticky top-0 bg-background pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">제한</h4>
            <LimitRulesEditor rules={limitRules} onChange={setLimitRules} />

            {apiKey.limits.length > 0 ? (
              <div className="space-y-1">
                <div className="text-xs font-medium text-muted-foreground">현재 사용량</div>
                <div className="space-y-1">
                  {apiKey.limits.map((limit) => (
                    <LimitUsageBar key={limit.id} limit={limit} />
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <DialogFooter className="mt-4">
          <Button type="submit" disabled={busy || form.formState.isSubmitting}>
            저장
          </Button>
        </DialogFooter>
      </form>
    </Form>
  );
}

function LimitUsageBar({ limit }: { limit: ApiKey["limits"][number] }) {
  const isCost = limit.limitType === "cost_usd";
  const percent = limit.maxValue > 0 ? Math.min(100, (limit.currentValue / limit.maxValue) * 100) : 0;
  const current = isCost ? `$${(limit.currentValue / 1_000_000).toFixed(2)}` : formatTokenCount(limit.currentValue);
  const max = isCost ? `$${(limit.maxValue / 1_000_000).toFixed(2)}` : formatTokenCount(limit.maxValue);
  const typeLabel = LIMIT_TYPE_SHORT[limit.limitType];
  const windowLabel = limit.limitWindow;
  const modelLabel = limit.modelFilter || "all";

  return (
    <div className="rounded border p-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">
          {typeLabel} ({windowLabel}, {modelLabel})
        </span>
        <span className="tabular-nums">
          {current} / {max}
        </span>
      </div>
      <div className="mt-1 h-1.5 w-full rounded-full bg-muted">
        <div
          className={`h-full rounded-full ${percent >= 90 ? "bg-destructive" : "bg-primary"}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

const LIMIT_TYPE_SHORT: Record<LimitType, string> = {
  total_tokens: "토큰",
  input_tokens: "입력",
  output_tokens: "출력",
  cost_usd: "비용",
  credits: "크레딧",
};

function formatTokenCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function ApiKeyEditDialog({ open, busy, apiKey, onOpenChange, onSubmit }: ApiKeyEditDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>API 키 수정</DialogTitle>
          <DialogDescription>제한과 수명 주기 설정을 수정합니다.</DialogDescription>
        </DialogHeader>

        {apiKey ? (
          <ApiKeyEditForm
            key={`${apiKey.id}:${open ? "open" : "closed"}`}
            apiKey={apiKey}
            busy={busy}
            onSubmit={onSubmit}
            onClose={() => onOpenChange(false)}
          />
        ) : (
          <p className="text-sm text-muted-foreground">수정할 API 키를 선택하세요.</p>
        )}
      </DialogContent>
    </Dialog>
  );
}
