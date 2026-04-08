import { useState } from "react";
import { Route } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { buildSettingsUpdateRequest } from "@/features/settings/payload";
import type { DashboardSettings, SettingsUpdateRequest } from "@/features/settings/schemas";

export type RoutingSettingsProps = {
  settings: DashboardSettings;
  busy: boolean;
  onSave: (payload: SettingsUpdateRequest) => Promise<void>;
};

export function RoutingSettings({ settings, busy, onSave }: RoutingSettingsProps) {
  const [cacheAffinityTtl, setCacheAffinityTtl] = useState(
    String(settings.openaiCacheAffinityMaxAgeSeconds),
  );

  const save = (patch: Partial<SettingsUpdateRequest>) =>
    void onSave(buildSettingsUpdateRequest(settings, patch));

  const parsedCacheAffinityTtl = Number.parseInt(cacheAffinityTtl, 10);
  const cacheAffinityTtlValid = Number.isInteger(parsedCacheAffinityTtl) && parsedCacheAffinityTtl > 0;
  const cacheAffinityTtlChanged =
    cacheAffinityTtlValid && parsedCacheAffinityTtl !== settings.openaiCacheAffinityMaxAgeSeconds;

  return (
    <section className="rounded-xl border bg-card p-5">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Route className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">라우팅</h3>
              <p className="text-xs text-muted-foreground">요청을 계정에 어떻게 분배할지 설정합니다.</p>
            </div>
          </div>
        </div>

        <div className="divide-y rounded-lg border">
          <div className="flex items-center justify-between gap-4 p-3">
            <div>
              <p className="text-sm font-medium">업스트림 스트림 전송 방식</p>
              <p className="text-xs text-muted-foreground">
                `codex-lb`가 스트리밍 응답을 위해 업스트림에 연결하는 방식을 선택합니다.
              </p>
            </div>
            <Select
              value={settings.upstreamStreamTransport}
              onValueChange={(value) =>
                save({ upstreamStreamTransport: value as "default" | "auto" | "http" | "websocket" })
              }
            >
              <SelectTrigger className="h-8 w-44 text-xs" disabled={busy}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent align="end">
                <SelectItem value="default">서버 기본값</SelectItem>
                <SelectItem value="auto">자동</SelectItem>
                <SelectItem value="http">Responses</SelectItem>
                <SelectItem value="websocket">웹소켓</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between gap-4 p-3">
            <div>
              <p className="text-sm font-medium">라우팅 전략</p>
              <p className="text-xs text-muted-foreground">요청을 계정에 분배하는 방식을 선택합니다.</p>
            </div>
            <Select
              value={settings.routingStrategy}
              onValueChange={(value) => save({ routingStrategy: value as "usage_weighted" | "round_robin" | "capacity_weighted" })}
            >
              <SelectTrigger className="h-8 w-44 text-xs" disabled={busy}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent align="end">
                <SelectItem value="capacity_weighted">용량 가중치</SelectItem>
                <SelectItem value="usage_weighted">사용량 가중치</SelectItem>
                <SelectItem value="round_robin">라운드 로빈</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between p-3">
            <div>
              <p className="text-sm font-medium">고정 스레드</p>
              <p className="text-xs text-muted-foreground">관련 요청을 같은 계정에 유지합니다.</p>
            </div>
            <Switch
              checked={settings.stickyThreadsEnabled}
              disabled={busy}
              onCheckedChange={(checked) => save({ stickyThreadsEnabled: checked })}
            />
          </div>

          <div className="flex items-center justify-between p-3">
            <div>
              <p className="text-sm font-medium">빠른 리셋 우선</p>
              <p className="text-xs text-muted-foreground">할당량이 더 빨리 초기화되는 계정으로 트래픽을 우선 보냅니다.</p>
            </div>
            <Switch
              checked={settings.preferEarlierResetAccounts}
              disabled={busy}
              onCheckedChange={(checked) => save({ preferEarlierResetAccounts: checked })}
            />
          </div>

          <div className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">프롬프트 캐시 affinity TTL</p>
              <p className="text-xs text-muted-foreground">
                OpenAI 스타일 프롬프트 캐시 매핑을 일정 시간 동안 유지합니다.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                min={1}
                step={1}
                inputMode="numeric"
                value={cacheAffinityTtl}
                disabled={busy}
                onChange={(event) => setCacheAffinityTtl(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && cacheAffinityTtlChanged) {
                    void save({ openaiCacheAffinityMaxAgeSeconds: parsedCacheAffinityTtl });
                  }
                }}
                className="h-8 w-28 text-xs"
              />
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-8 text-xs"
                disabled={busy || !cacheAffinityTtlChanged}
                onClick={() => void save({ openaiCacheAffinityMaxAgeSeconds: parsedCacheAffinityTtl })}
              >
                TTL 저장
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
