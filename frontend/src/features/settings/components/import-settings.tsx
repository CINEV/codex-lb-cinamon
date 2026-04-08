import { Upload } from "lucide-react";

import { Switch } from "@/components/ui/switch";
import { buildSettingsUpdateRequest } from "@/features/settings/payload";
import type { DashboardSettings, SettingsUpdateRequest } from "@/features/settings/schemas";

export type ImportSettingsProps = {
  settings: DashboardSettings;
  busy: boolean;
  onSave: (payload: SettingsUpdateRequest) => Promise<void>;
};

export function ImportSettings({ settings, busy, onSave }: ImportSettingsProps) {
  const save = (patch: Partial<SettingsUpdateRequest>) =>
    void onSave(buildSettingsUpdateRequest(settings, patch));

  return (
    <section className="rounded-xl border bg-card p-5">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Upload className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">가져오기</h3>
              <p className="text-xs text-muted-foreground">계정 가져오기 시 중복 처리 방식을 설정합니다.</p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between rounded-lg border p-3">
          <div>
            <p className="text-sm font-medium">덮어쓰기 없이 가져오기 허용</p>
            <p className="text-xs text-muted-foreground">
              중복된 가져오기를 기존 계정을 대체하지 않고 별도 계정으로 유지합니다.
            </p>
          </div>
          <Switch
            checked={settings.importWithoutOverwrite}
            disabled={busy}
            onCheckedChange={(checked) => save({ importWithoutOverwrite: checked })}
          />
        </div>
      </div>
    </section>
  );
}
