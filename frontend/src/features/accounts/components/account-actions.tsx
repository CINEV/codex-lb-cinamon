import { Download, Pause, Pencil, Play, RefreshCw, Trash2, Zap } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { AccountSummary } from "@/features/accounts/schemas";

export type AccountActionsProps = {
  account: AccountSummary;
  busy: boolean;
  onEditPlatform: (account: AccountSummary) => void;
  onPause: (accountId: string) => void;
  onResume: (accountId: string) => void;
  onDelete: (accountId: string) => void;
  onReauth: () => void;
  onExport: (accountId: string) => void;
  onLimitWarmupChange: (accountId: string, enabled: boolean) => void;
};

export function AccountActions({
  account,
  busy,
  onEditPlatform,
  onPause,
  onResume,
  onDelete,
  onReauth,
  onExport,
  onLimitWarmupChange,
}: AccountActionsProps) {
  const supportsChatGptAccountActions = account.providerKind !== "openai_platform";
  const supportsPlatformEdit = account.providerKind === "openai_platform";

  return (
    <div className="flex flex-wrap gap-2 border-t pt-4">
      {supportsPlatformEdit ? (
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-xs"
          onClick={() => onEditPlatform(account)}
          disabled={busy}
        >
          <Pencil className="h-3.5 w-3.5" />
          Edit
        </Button>
      ) : null}

      {account.status === "paused" ? (
        <Button
          type="button"
          size="sm"
          className="h-8 gap-1.5 text-xs"
          onClick={() => onResume(account.accountId)}
          disabled={busy}
        >
          <Play className="h-3.5 w-3.5" />
          Resume
        </Button>
      ) : (
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-xs"
          onClick={() => onPause(account.accountId)}
          disabled={busy}
        >
          <Pause className="h-3.5 w-3.5" />
          Pause
        </Button>
      )}

      {supportsChatGptAccountActions && account.status === "deactivated" ? (
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-xs"
          onClick={onReauth}
          disabled={busy}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Re-authenticate
        </Button>
      ) : null}

      {supportsChatGptAccountActions ? (
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-xs"
          onClick={() => onLimitWarmupChange(account.accountId, !account.limitWarmupEnabled)}
          disabled={busy}
        >
          <Zap className="h-3.5 w-3.5" />
          {account.limitWarmupEnabled ? "Disable warm-up" : "Enable warm-up"}
        </Button>
      ) : null}

      {supportsChatGptAccountActions ? (
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-xs"
          onClick={() => onExport(account.accountId)}
          disabled={busy}
        >
          <Download className="h-3.5 w-3.5" />
          Export
        </Button>
      ) : null}

      <Button
        type="button"
        size="sm"
        variant="destructive"
        className="h-8 gap-1.5 text-xs"
        onClick={() => onDelete(account.accountId)}
        disabled={busy}
      >
        <Trash2 className="h-3.5 w-3.5" />
        Delete
      </Button>
    </div>
  );
}
