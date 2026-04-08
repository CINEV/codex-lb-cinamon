import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  createPlatformIdentity,
  deleteAccount,
  getAccountTrends,
  importAccount,
  listAccounts,
  pauseAccount,
  reactivateAccount,
  updatePlatformIdentity,
} from "@/features/accounts/api";
import type { PlatformIdentityUpdateRequest } from "@/features/accounts/schemas";

function invalidateAccountRelatedQueries(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["accounts", "list"] });
  void queryClient.invalidateQueries({ queryKey: ["dashboard", "overview"] });
}

/**
 * Account mutation actions without the polling query.
 * Use this when you need account actions but already have account data
 * from another source (e.g. the dashboard overview query).
 */
export function useAccountMutations() {
  const queryClient = useQueryClient();

  const importMutation = useMutation({
    mutationFn: importAccount,
    onSuccess: () => {
      toast.success("계정을 가져왔습니다");
      invalidateAccountRelatedQueries(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message || "가져오기에 실패했습니다");
    },
  });

  const createPlatformMutation = useMutation({
    mutationFn: createPlatformIdentity,
    onSuccess: () => {
      toast.success("OpenAI Platform 대체 ID를 추가했습니다");
      invalidateAccountRelatedQueries(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message || "OpenAI Platform 대체 ID를 추가하지 못했습니다");
    },
  });

  const updatePlatformMutation = useMutation({
    mutationFn: ({
      accountId,
      payload,
    }: {
      accountId: string;
      payload: PlatformIdentityUpdateRequest;
    }) => updatePlatformIdentity(accountId, payload),
    onSuccess: () => {
      toast.success("OpenAI Platform 대체 ID를 수정했습니다");
      invalidateAccountRelatedQueries(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message || "OpenAI Platform 대체 ID를 수정하지 못했습니다");
    },
  });

  const pauseMutation = useMutation({
    mutationFn: pauseAccount,
    onSuccess: () => {
      toast.success("계정을 일시 중지했습니다");
      invalidateAccountRelatedQueries(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message || "일시 중지에 실패했습니다");
    },
  });

  const resumeMutation = useMutation({
    mutationFn: reactivateAccount,
    onSuccess: () => {
      toast.success("계정을 다시 활성화했습니다");
      invalidateAccountRelatedQueries(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message || "재활성화에 실패했습니다");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      toast.success("계정을 삭제했습니다");
      invalidateAccountRelatedQueries(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message || "삭제에 실패했습니다");
    },
  });

  return {
    importMutation,
    createPlatformMutation,
    updatePlatformMutation,
    pauseMutation,
    resumeMutation,
    deleteMutation,
  };
}

export function useAccountTrends(accountId: string | null) {
  return useQuery({
    queryKey: ["accounts", "trends", accountId],
    queryFn: () => getAccountTrends(accountId!),
    enabled: !!accountId,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    refetchIntervalInBackground: false,
  });
}

export function useAccounts() {
  const accountsQuery = useQuery({
    queryKey: ["accounts", "list"],
    queryFn: listAccounts,
    select: (data) => data.accounts,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const mutations = useAccountMutations();

  return { accountsQuery, ...mutations };
}
