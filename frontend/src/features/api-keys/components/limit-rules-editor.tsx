import { useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { LimitRuleCard } from "@/features/api-keys/components/limit-rule-card";
import type { LimitRuleCreate } from "@/features/api-keys/schemas";

export type LimitRulesEditorProps = {
  rules: LimitRuleCreate[];
  onChange: (rules: LimitRuleCreate[]) => void;
};

function makeDefaultRule(): LimitRuleCreate {
  return {
    limitType: "total_tokens",
    limitWindow: "weekly",
    maxValue: 0,
    modelFilter: null,
  };
}

export function LimitRulesEditor({ rules, onChange }: LimitRulesEditorProps) {
  const [advanced, setAdvanced] = useState(() => {
    if (rules.length === 0) return false;
    // If any non-standard rule exists, start in advanced mode
    return rules.some(
      (r) =>
        (r.limitType !== "total_tokens" && r.limitType !== "cost_usd") ||
        r.limitWindow !== "weekly" ||
        (r.modelFilter !== null && r.modelFilter !== undefined),
    );
  });

  // Derive basic mode values from rules
  const weeklyTokenRule = rules.find(
    (r) => r.limitType === "total_tokens" && r.limitWindow === "weekly" && !r.modelFilter,
  );
  const weeklyCostRule = rules.find(
    (r) => r.limitType === "cost_usd" && r.limitWindow === "weekly" && !r.modelFilter,
  );

  const handleBasicTokenChange = (raw: string) => {
    const val = raw ? parseInt(raw, 10) : 0;
    const otherRules = rules.filter(
      (r) => !(r.limitType === "total_tokens" && r.limitWindow === "weekly" && !r.modelFilter),
    );
    if (val > 0) {
      onChange([
        ...otherRules,
        { limitType: "total_tokens", limitWindow: "weekly", maxValue: val, modelFilter: null },
      ]);
    } else {
      onChange(otherRules);
    }
  };

  const handleBasicCostChange = (raw: string) => {
    const usd = raw ? parseFloat(raw) : 0;
    const otherRules = rules.filter(
      (r) => !(r.limitType === "cost_usd" && r.limitWindow === "weekly" && !r.modelFilter),
    );
    if (usd > 0) {
      onChange([
        ...otherRules,
        {
          limitType: "cost_usd",
          limitWindow: "weekly",
          maxValue: Math.round(usd * 1_000_000),
          modelFilter: null,
        },
      ]);
    } else {
      onChange(otherRules);
    }
  };

  const addRule = () => {
    onChange([...rules, makeDefaultRule()]);
  };

  const updateRule = (index: number, updated: LimitRuleCreate) => {
    const next = [...rules];
    next[index] = updated;
    onChange(next);
  };

  const removeRule = (index: number) => {
    onChange(rules.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">제한</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">고급</span>
          <Switch
            checked={advanced}
            onCheckedChange={setAdvanced}
          />
        </div>
      </div>

      {!advanced ? (
        <div className="space-y-2">
          <div>
            <label className="text-xs text-muted-foreground">주간 토큰 제한</label>
            <Input
              type="number"
              min={1}
              value={weeklyTokenRule ? String(weeklyTokenRule.maxValue) : ""}
              onChange={(e) => handleBasicTokenChange(e.target.value)}
              placeholder="제한 없음"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">주간 비용 제한 ($)</label>
            <Input
              type="number"
              min={0.01}
              step={0.01}
              value={
                weeklyCostRule && weeklyCostRule.maxValue > 0
                  ? String(weeklyCostRule.maxValue / 1_000_000)
                  : ""
              }
              onChange={(e) => handleBasicCostChange(e.target.value)}
              placeholder="제한 없음"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {rules.map((rule, index) => (
            <LimitRuleCard
              key={index}
              rule={rule}
              onChange={(updated) => updateRule(index, updated)}
              onRemove={() => removeRule(index)}
            />
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full"
            onClick={addRule}
          >
            <Plus className="mr-1 size-3.5" />
            제한 규칙 추가
          </Button>
          {rules.length > 1 ? (
            <p className="text-xs text-muted-foreground">
              모든 규칙은 함께 적용됩니다(AND). 하나라도 초과하면 요청이 차단됩니다.
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}
