import { Switch } from "@/components/ui/switch";

export type ApiKeyAuthToggleProps = {
  enabled: boolean;
  disabled?: boolean;
  onChange: (enabled: boolean) => void;
};

export function ApiKeyAuthToggle({ enabled, disabled = false, onChange }: ApiKeyAuthToggleProps) {
  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <div className="space-y-1">
        <p className="text-sm font-medium">API 키 인증</p>
        <p className="text-xs text-muted-foreground">
          들어오는 `/v1/*` 요청에 API 키를 요구합니다.
        </p>
      </div>
      <Switch checked={enabled} disabled={disabled} onCheckedChange={onChange} />
    </div>
  );
}
