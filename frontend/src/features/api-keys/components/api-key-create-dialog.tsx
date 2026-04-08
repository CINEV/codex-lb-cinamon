import { useState } from "react";
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
import { ExpiryPicker } from "@/features/api-keys/components/expiry-picker";
import { LimitRulesEditor } from "@/features/api-keys/components/limit-rules-editor";
import { ModelMultiSelect } from "@/features/api-keys/components/model-multi-select";
import type { ApiKeyCreateRequest, LimitRuleCreate, ServiceTierType } from "@/features/api-keys/schemas";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const formSchema = z.object({
  name: z.string().min(1, "이름은 필수입니다"),
});

type FormValues = z.infer<typeof formSchema>;

export type ApiKeyCreateDialogProps = {
  open: boolean;
  busy: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: ApiKeyCreateRequest) => Promise<void>;
};

export function ApiKeyCreateDialog({ open, busy, onOpenChange, onSubmit }: ApiKeyCreateDialogProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { name: "" },
  });

  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [limitRules, setLimitRules] = useState<LimitRuleCreate[]>([]);
  const [expiresAt, setExpiresAt] = useState<Date | null>(null);
  const [enforcedModel, setEnforcedModel] = useState("");
  const [enforcedReasoningEffort, setEnforcedReasoningEffort] = useState("none");
  const [enforcedServiceTier, setEnforcedServiceTier] = useState("none");

  const handleSubmit = async (values: FormValues) => {
    const validLimits = limitRules.filter((r) => r.maxValue > 0);
    const payload: ApiKeyCreateRequest = {
      name: values.name,
      allowedModels: selectedModels.length > 0 ? selectedModels : undefined,
      enforcedModel: enforcedModel.trim() ? enforcedModel.trim() : null,
      enforcedReasoningEffort: enforcedReasoningEffort === "none" ? null : enforcedReasoningEffort as "minimal" | "low" | "medium" | "high" | "xhigh",
      enforcedServiceTier: enforcedServiceTier === "none" ? null : enforcedServiceTier as ServiceTierType,
      expiresAt: expiresAt?.toISOString(),
      limits: validLimits.length > 0 ? validLimits : undefined,
    };
    try {
      await onSubmit(payload);
    } catch {
      return;
    }
    form.reset();
    setSelectedModels([]);
    setLimitRules([]);
    setExpiresAt(null);
    setEnforcedModel("");
    setEnforcedReasoningEffort("none");
    setEnforcedServiceTier("none");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>API 키 생성</DialogTitle>
          <DialogDescription>이 키의 제한 사항과 만료 시간을 설정합니다.</DialogDescription>
        </DialogHeader>

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
                  <label className="text-sm font-medium">허용 모델</label>
                  <ModelMultiSelect value={selectedModels} onChange={setSelectedModels} />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium">강제 모델</label>
                  <Input
                    value={enforcedModel}
                    onChange={(e) => setEnforcedModel(e.target.value)}
                    placeholder="예: gpt-5.3-codex"
                    autoComplete="off"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium">강제 추론 수준</label>
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
                  <label className="text-sm font-medium">강제 서비스 티어</label>
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
                  <label className="text-sm font-medium">만료</label>
                  <ExpiryPicker value={expiresAt} onChange={setExpiresAt} />
                </div>
              </div>

              {/* Right column — Limits */}
              <div className="max-h-[55vh] space-y-3 overflow-y-auto overscroll-contain pl-1 pr-2 max-sm:mt-3 max-sm:border-t max-sm:pt-3">
                <h4 className="sticky top-0 bg-background pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">제한</h4>
                <LimitRulesEditor rules={limitRules} onChange={setLimitRules} />
              </div>
            </div>

            <DialogFooter className="mt-4">
              <Button type="submit" disabled={busy || form.formState.isSubmitting}>
                생성
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
