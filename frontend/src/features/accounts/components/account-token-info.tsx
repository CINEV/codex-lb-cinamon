import type { AccountSummary } from "@/features/accounts/schemas";
import {
  formatAccessTokenLabel,
  formatIdTokenLabel,
  formatRefreshTokenLabel,
} from "@/utils/formatters";

export type AccountTokenInfoProps = {
  account: AccountSummary;
};

export function AccountTokenInfo({ account }: AccountTokenInfoProps) {
  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">토큰 상태</h3>
      <dl className="space-y-2 text-xs">
        <div className="flex items-center justify-between gap-2">
          <dt className="text-muted-foreground">액세스</dt>
          <dd className="font-medium">{formatAccessTokenLabel(account.auth)}</dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="text-muted-foreground">리프레시</dt>
          <dd className="font-medium">{formatRefreshTokenLabel(account.auth)}</dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="text-muted-foreground">ID 토큰</dt>
          <dd className="font-medium">{formatIdTokenLabel(account.auth)}</dd>
        </div>
      </dl>
    </div>
  );
}
