import { ChevronDown, ChevronUp, KeyRound, Plus, Search, Upload } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AccountListItem } from "@/features/accounts/components/account-list-item";
import { WindowsOauthHelp } from "@/features/accounts/components/windows-oauth-help";
import type { AccountSummary } from "@/features/accounts/schemas";
import { buildDuplicateAccountIdSet } from "@/utils/account-identifiers";
import { formatSlug } from "@/utils/formatters";

const STATUS_FILTER_OPTIONS = ["all", "active", "paused", "rate_limited", "quota_exceeded", "deactivated"];

export type AccountListProps = {
  accounts: AccountSummary[];
  selectedAccountId: string | null;
  platformIdentityRegistered: boolean;
  platformPrerequisiteSatisfied: boolean;
  onSelect: (accountId: string) => void;
  onOpenImport: () => void;
  onOpenOauth: () => void;
  onOpenPlatform: () => void;
};

export function AccountList({
  accounts,
  selectedAccountId,
  platformIdentityRegistered,
  platformPrerequisiteSatisfied,
  onSelect,
  onOpenImport,
  onOpenOauth,
  onOpenPlatform,
}: AccountListProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [helpOpen, setHelpOpen] = useState(false);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return accounts.filter((account) => {
      if (statusFilter !== "all" && account.status !== statusFilter) {
        return false;
      }
      if (!needle) {
        return true;
      }
      return (
        account.email.toLowerCase().includes(needle) ||
        (account.label ?? "").toLowerCase().includes(needle) ||
        account.accountId.toLowerCase().includes(needle) ||
        account.planType.toLowerCase().includes(needle) ||
        (account.providerKind ?? "").toLowerCase().includes(needle) ||
        (account.routingSubjectId ?? "").toLowerCase().includes(needle) ||
        (account.organization ?? "").toLowerCase().includes(needle) ||
        (account.project ?? "").toLowerCase().includes(needle) ||
        (account.eligibleRouteFamilies ?? []).some((family) => family.toLowerCase().includes(needle))
      );
    });
  }, [accounts, search, statusFilter]);

  const duplicateAccountIds = useMemo(() => buildDuplicateAccountIdSet(accounts), [accounts]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60" aria-hidden />
          <Input
            placeholder="계정 검색..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="h-8 pl-8"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger size="sm" className="w-32 shrink-0">
            <SelectValue placeholder="상태" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_FILTER_OPTIONS.map((option) => (
              <SelectItem key={option} value={option}>
                {option === "all" ? "전체 상태" : formatSlug(option)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <Button type="button" size="sm" variant="outline" onClick={onOpenImport} className="h-8 gap-1.5 px-2 text-xs">
          <Upload className="h-3.5 w-3.5" />
          가져오기
        </Button>
        <Button type="button" size="sm" onClick={onOpenOauth} className="h-8 gap-1.5 px-2 text-xs">
          <Plus className="h-3.5 w-3.5" />
          계정 추가
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={onOpenPlatform}
          disabled={platformIdentityRegistered || !platformPrerequisiteSatisfied}
          className="h-8 gap-1.5 px-2 text-xs"
        >
          <KeyRound className="h-3.5 w-3.5" />
          API 키 추가
        </Button>
      </div>
      {platformIdentityRegistered ? (
        <p className="text-xs text-muted-foreground">
          Platform 폴백 키는 이미 등록되어 있습니다. 현재는 하나만 허용됩니다.
        </p>
      ) : !platformPrerequisiteSatisfied ? (
        <p className="text-xs text-muted-foreground">
          Platform 폴백 키를 등록하기 전에 ChatGPT 계정을 추가하거나 다시 활성화하세요.
        </p>
      ) : null}

      <div>
        <Button
          type="button"
          variant="link"
          size="sm"
          className="h-auto px-0 text-xs"
          onClick={() => setHelpOpen((current) => !current)}
        >
          도움이 필요하신가요?
          {helpOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </Button>
      </div>

      {helpOpen ? <WindowsOauthHelp /> : null}

      <div className="max-h-[calc(100vh-16rem)] space-y-1 overflow-y-auto p-1">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-6 text-center">
            <p className="text-sm font-medium text-muted-foreground">일치하는 계정이 없습니다</p>
            <p className="text-xs text-muted-foreground/70">필터를 조정해보세요.</p>
          </div>
        ) : (
          filtered.map((account) => (
            <AccountListItem
              key={account.accountId}
              account={account}
              selected={account.accountId === selectedAccountId}
              showAccountId={duplicateAccountIds.has(account.accountId)}
              onSelect={onSelect}
            />
          ))
        )}
      </div>
    </div>
  );
}
