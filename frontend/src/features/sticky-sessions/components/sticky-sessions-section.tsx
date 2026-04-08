import { useEffect, useMemo, useState } from "react";
import { Pin } from "lucide-react";

import { AlertMessage } from "@/components/alert-message";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { SpinnerBlock } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PaginationControls } from "@/features/dashboard/components/filters/pagination-controls";
import { useStickySessions } from "@/features/sticky-sessions/hooks/use-sticky-sessions";
import type {
  StickySessionEntry,
  StickySessionIdentifier,
  StickySessionKind,
  StickySessionProviderKind,
  StickySessionSortBy,
  StickySessionSortDir,
} from "@/features/sticky-sessions/schemas";
import { useDialogState } from "@/hooks/use-dialog-state";
import { getErrorMessageOrNull } from "@/utils/errors";
import { formatProviderLabel, formatTimeLong } from "@/utils/formatters";

function kindLabel(kind: StickySessionKind): string {
  switch (kind) {
    case "codex_session":
      return "Codex 세션";
    case "sticky_thread":
      return "고정 스레드";
    case "prompt_cache":
      return "프롬프트 캐시";
  }
}

function affinityScopeLabel(value: StickySessionEntry["affinityScope"]): string {
  switch (value) {
    case "chatgpt_continuity":
      return "ChatGPT 연속성";
    case "provider_prompt_cache":
      return "프롬프트 캐시 affinity";
    case "provider_scoped":
      return "공급자 범위";
  }
}

function stickySessionRowId(entry: StickySessionIdentifier): string {
  return `${entry.providerKind}:${entry.kind}:${entry.key}`;
}

const EMPTY_STICKY_SESSION_ENTRIES: StickySessionEntry[] = [];

function nextSortDirection(currentSortBy: StickySessionSortBy, currentSortDir: StickySessionSortDir, target: StickySessionSortBy) {
  if (currentSortBy != target) {
    return target === "updated_at" ? "desc" : "asc";
  }
  return currentSortDir === "asc" ? "desc" : "asc";
}

function sortIndicator(currentSortBy: StickySessionSortBy, currentSortDir: StickySessionSortDir, target: StickySessionSortBy) {
  if (currentSortBy !== target) {
    return null;
  }
  return currentSortDir === "asc" ? " ↑" : " ↓";
}

export function StickySessionsSection() {
  const {
    params,
    setAccountQuery,
    setKeyQuery,
    setProviderKind,
    setSort,
    setLimit,
    setOffset,
    stickySessionsQuery,
    deleteMutation,
    deleteFilteredMutation,
    purgeMutation,
  } = useStickySessions();
  const deleteDialog = useDialogState<StickySessionIdentifier>();
  const deleteSelectedDialog = useDialogState<StickySessionIdentifier[]>();
  const deleteFilteredDialog = useDialogState<number>();
  const purgeDialog = useDialogState();
  const [selectedRowIds, setSelectedRowIds] = useState<string[]>([]);

  const mutationError = useMemo(
    () =>
      getErrorMessageOrNull(stickySessionsQuery.error) ||
      getErrorMessageOrNull(deleteMutation.error) ||
      getErrorMessageOrNull(deleteFilteredMutation.error) ||
      getErrorMessageOrNull(purgeMutation.error),
    [stickySessionsQuery.error, deleteMutation.error, deleteFilteredMutation.error, purgeMutation.error],
  );

  const entries = stickySessionsQuery.data?.entries ?? EMPTY_STICKY_SESSION_ENTRIES;
  const staleCount = stickySessionsQuery.data?.stalePromptCacheCount ?? 0;
  const total = stickySessionsQuery.data?.total ?? 0;
  const hasMore = stickySessionsQuery.data?.hasMore ?? false;
  const busy = deleteMutation.isPending || deleteFilteredMutation.isPending || purgeMutation.isPending;
  const hasEntries = entries.length > 0;
  const hasAnyRows = total > 0;
  const hasActiveFilter =
    params.providerKind !== null || params.accountQuery.trim().length > 0 || params.keyQuery.trim().length > 0;
  const visibleRowIdSet = useMemo(() => new Set(entries.map((entry) => stickySessionRowId(entry))), [entries]);
  const selectedRowIdSet = useMemo(() => new Set(selectedRowIds), [selectedRowIds]);
  const selectedEntries = useMemo(
    () =>
      entries
        .filter((entry) => selectedRowIdSet.has(stickySessionRowId(entry)))
        .map(({ key, kind, providerKind }) => ({ key, kind, providerKind })),
    [entries, selectedRowIdSet],
  );
  const selectedCount = selectedEntries.length;
  const allVisibleSelected = hasEntries && selectedCount === entries.length;
  const someVisibleSelected = selectedCount > 0 && !allVisibleSelected;
  const selectedDeleteTargets = deleteSelectedDialog.data ?? [];
  const selectedDeleteCount = selectedDeleteTargets.length;

  const providerFilters: Array<{ label: string; value: StickySessionProviderKind | null }> = [
    { label: "전체 공급자", value: null },
    { label: "ChatGPT 웹", value: "chatgpt_web" },
    { label: "OpenAI 플랫폼", value: "openai_platform" },
  ];

  useEffect(() => {
    if (!stickySessionsQuery.isLoading && total > 0 && entries.length === 0 && params.offset > 0) {
      const lastValidOffset = Math.max(0, Math.floor((total - 1) / params.limit) * params.limit);
      if (lastValidOffset !== params.offset) {
        setOffset(lastValidOffset);
      }
    }
  }, [entries.length, params.limit, params.offset, setOffset, stickySessionsQuery.isLoading, total]);

  const setSelected = (target: StickySessionIdentifier, checked: boolean) => {
    const rowId = stickySessionRowId(target);
    setSelectedRowIds((current) => {
      if (checked) {
        return current.includes(rowId) ? current : [...current, rowId];
      }
      return current.filter((value) => value !== rowId);
    });
  };

  const setAllVisibleSelected = (checked: boolean) => {
    setSelectedRowIds((current) => {
      const remaining = current.filter((rowId) => !visibleRowIdSet.has(rowId));
      return checked ? [...remaining, ...entries.map((entry) => stickySessionRowId(entry))] : remaining;
    });
  };

  return (
    <section className="space-y-3 rounded-xl border bg-card p-5">
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
          <Pin className="h-4 w-4 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">고정 세션</h3>
          <p className="text-xs text-muted-foreground">
            유지되는 매핑을 확인하고 오래된 프롬프트 캐시 affinity 항목을 정리합니다.
          </p>
        </div>
      </div>

      {mutationError ? <AlertMessage variant="error">{mutationError}</AlertMessage> : null}

      <div className="grid gap-2 sm:grid-cols-2">
        <Input
          aria-label="계정으로 고정 세션 필터링"
          placeholder="계정으로 필터링..."
          value={params.accountQuery}
          onChange={(event) => setAccountQuery(event.target.value)}
        />
        <Input
          aria-label="키로 고정 세션 필터링"
          placeholder="키로 필터링..."
          value={params.keyQuery}
          onChange={(event) => setKeyQuery(event.target.value)}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {providerFilters.map((filter) => {
          const active = params.providerKind === filter.value;
          return (
            <Button
              key={filter.label}
              type="button"
              size="sm"
              variant={active ? "default" : "outline"}
              className="h-8 text-xs"
              onClick={() => setProviderKind(filter.value)}
            >
              {filter.label}
            </Button>
          );
        })}
      </div>

      <div className="flex flex-col gap-3 rounded-lg border px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">표시 행 수</span>
            <span className="text-sm font-medium tabular-nums">{total}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">오래된 프롬프트 캐시</span>
            <span className="text-sm font-medium tabular-nums">{staleCount}</span>
          </div>
          {selectedCount > 0 ? (
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">선택됨</span>
              <span className="text-sm font-medium tabular-nums">{selectedCount}</span>
            </div>
          ) : null}
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 text-xs"
            disabled={busy || !hasActiveFilter || total === 0}
            onClick={() => deleteFilteredDialog.show(total)}
          >
            필터된 항목 삭제
          </Button>
          <Button
            type="button"
            size="sm"
            variant="destructive"
            className="h-8 text-xs"
            disabled={busy || selectedCount === 0}
            onClick={() => deleteSelectedDialog.show(selectedEntries)}
          >
            세션 삭제
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 text-xs"
            disabled={busy || staleCount === 0}
            onClick={() => purgeDialog.show()}
          >
            오래된 항목 정리
          </Button>
        </div>
      </div>

      {stickySessionsQuery.isLoading && !stickySessionsQuery.data ? (
        <div className="py-8">
          <SpinnerBlock />
        </div>
      ) : !hasAnyRows ? (
        <EmptyState
          icon={Pin}
          title="고정 세션이 없습니다"
          description="라우팅된 요청이 매핑을 만들면 여기에 표시됩니다."
        />
      ) : (
        <>
          {hasEntries ? (
            <div className="overflow-x-auto rounded-xl border">
              <Table className="table-fixed">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[5%] min-w-[3rem] pl-4 text-[11px] uppercase tracking-wider text-muted-foreground/80">
                      <Checkbox
                        aria-label="현재 페이지의 고정 세션 전체 선택"
                        checked={allVisibleSelected ? true : someVisibleSelected ? "indeterminate" : false}
                        disabled={busy || !hasEntries}
                        onCheckedChange={(checked) => setAllVisibleSelected(checked === true)}
                      />
                    </TableHead>
                    <TableHead className="w-[25%] min-w-[14rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">
                      <button
                        type="button"
                        className="cursor-pointer text-left transition-colors hover:text-foreground"
                        onClick={() => setSort("key", nextSortDirection(params.sortBy, params.sortDir, "key"))}
                      >
                        {`Key${sortIndicator(params.sortBy, params.sortDir, "key") ?? ""}`}
                      </button>
                    </TableHead>
                    <TableHead className="w-[14%] min-w-[8rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">
                      종류
                    </TableHead>
                    <TableHead className="w-[18%] min-w-[9rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">
                      <button
                        type="button"
                        className="cursor-pointer text-left transition-colors hover:text-foreground"
                        onClick={() => setSort("account", nextSortDirection(params.sortBy, params.sortDir, "account"))}
                      >
                        {`계정${sortIndicator(params.sortBy, params.sortDir, "account") ?? ""}`}
                      </button>
                    </TableHead>
                    <TableHead className="w-[16%] min-w-[9rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">
                      <button
                        type="button"
                        className="cursor-pointer text-left transition-colors hover:text-foreground"
                        onClick={() =>
                          setSort("updated_at", nextSortDirection(params.sortBy, params.sortDir, "updated_at"))
                        }
                      >
                        {`업데이트${sortIndicator(params.sortBy, params.sortDir, "updated_at") ?? ""}`}
                      </button>
                    </TableHead>
                    <TableHead className="w-[16%] min-w-[9rem] text-[11px] uppercase tracking-wider text-muted-foreground/80">
                      만료
                    </TableHead>
                    <TableHead className="w-[6%] min-w-[4.5rem] pr-4 text-right align-middle text-[11px] uppercase tracking-wider text-muted-foreground/80">
                      작업
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {entries.map((entry) => {
                    const updated = formatTimeLong(entry.updatedAt);
                    const expires = entry.expiresAt ? formatTimeLong(entry.expiresAt) : null;
                    const selected = selectedRowIdSet.has(stickySessionRowId(entry));
                    return (
                      <TableRow
                        key={`${entry.providerKind}:${entry.kind}:${entry.key}`}
                        data-state={selected ? "selected" : undefined}
                      >
                        <TableCell className="pl-4">
                          <Checkbox
                            aria-label={`고정 세션 ${entry.key} 선택`}
                            checked={selected}
                            disabled={busy}
                            onCheckedChange={(checked) => setSelected(entry, checked === true)}
                          />
                        </TableCell>
                        <TableCell className="max-w-[18rem] truncate font-mono text-xs" title={entry.key}>
                          {entry.key}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{kindLabel(entry.kind)}</Badge>
                        </TableCell>
                        <TableCell className="truncate text-xs">
                          <div className="truncate font-medium">{entry.displayName}</div>
                          <div className="truncate text-[11px] text-muted-foreground">
                            <span>{formatProviderLabel(entry.providerKind)}</span>
                            <span aria-hidden="true"> · </span>
                            <span>{entry.routingSubjectId}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          <div>{updated.date} {updated.time}</div>
                          <div className="text-[11px]">{affinityScopeLabel(entry.affinityScope)}</div>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {entry.isStale ? (
                            <Badge variant="secondary">오래됨</Badge>
                          ) : expires ? (
                            `${expires.date} ${expires.time}`
                          ) : (
                            "지속됨"
                          )}
                        </TableCell>
                        <TableCell className="pr-4 text-right">
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:text-destructive"
                            disabled={busy}
                            onClick={() =>
                              deleteDialog.show({ key: entry.key, kind: entry.kind, providerKind: entry.providerKind })
                            }
                          >
                            제거
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : (
            <EmptyState
              icon={Pin}
              title="이 페이지에는 고정 세션이 없습니다"
              description="현재 페이지가 비어 있습니다. 페이지 이동으로 다른 페이지를 확인하세요."
            />
          )}
          <div className="flex justify-end pt-3">
            <PaginationControls
              total={total}
              limit={params.limit}
              offset={params.offset}
              hasMore={hasMore}
              onLimitChange={setLimit}
              onOffsetChange={setOffset}
            />
          </div>
        </>
      )}

      <ConfirmDialog
        open={deleteDialog.open}
        title="고정 세션 제거"
        description={
          deleteDialog.data
            ? `${formatProviderLabel(deleteDialog.data.providerKind)}의 ${kindLabel(deleteDialog.data.kind)} 매핑 ${deleteDialog.data.key} 는 앞으로 요청을 고정하지 않습니다.`
            : ""
        }
        confirmLabel="삭제"
        onOpenChange={deleteDialog.onOpenChange}
        onConfirm={() => {
          if (!deleteDialog.data) {
            return;
          }
          void deleteMutation.mutateAsync([deleteDialog.data]).finally(() => {
            deleteDialog.hide();
          });
        }}
      />

      <ConfirmDialog
        open={deleteSelectedDialog.open}
        title="선택한 고정 세션 삭제"
        description={
          selectedDeleteCount === 1
            ? "선택한 고정 세션을 삭제할까요? 실패한 삭제는 따로 안내됩니다."
            : `선택한 고정 세션 ${selectedDeleteCount}개를 삭제할까요? 실패한 삭제는 따로 안내됩니다.`
        }
        confirmLabel="세션 삭제"
        onOpenChange={deleteSelectedDialog.onOpenChange}
        onConfirm={() => {
          if (selectedDeleteTargets.length === 0) {
            return;
          }
          void deleteMutation.mutateAsync(selectedDeleteTargets).then((response) => {
            setSelectedRowIds(response.failed.map((entry) => stickySessionRowId(entry)));
          }).finally(() => {
            deleteSelectedDialog.hide();
          });
        }}
      />

      <ConfirmDialog
        open={deleteFilteredDialog.open}
        title="필터된 고정 세션 삭제"
        description={`현재 필터와 일치하는 고정 세션 ${deleteFilteredDialog.data ?? 0}개를 모두 삭제할까요?${params.providerKind ? ` (${formatProviderLabel(params.providerKind)})` : ""}`}
        confirmLabel="필터된 항목 삭제"
        onOpenChange={deleteFilteredDialog.onOpenChange}
        onConfirm={() => {
          void deleteFilteredMutation.mutateAsync().then(() => {
            setSelectedRowIds([]);
          }).finally(() => {
            deleteFilteredDialog.hide();
          });
        }}
      />

      <ConfirmDialog
        open={purgeDialog.open}
        title="오래된 프롬프트 캐시 매핑 정리"
        description="만료된 프롬프트 캐시 항목만 삭제됩니다. 지속 세션과 고정 스레드 매핑은 유지됩니다."
        confirmLabel="정리"
        onOpenChange={purgeDialog.onOpenChange}
        onConfirm={() => {
          void purgeMutation.mutateAsync(true).finally(() => {
            purgeDialog.hide();
          });
        }}
      />
    </section>
  );
}
