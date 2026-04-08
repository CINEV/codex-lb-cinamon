import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  createApiKey,
  deleteApiKey,
  getApiKeyTrends,
  getApiKeyUsage7Day,
  listApiKeys,
  regenerateApiKey,
  updateApiKey,
} from "@/features/apis/api";
import type {
  ApiKeyCreateRequest,
  ApiKeyUpdateRequest,
} from "@/features/api-keys/schemas";

function invalidateApiKeys(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["api-keys", "list"] });
  void queryClient.invalidateQueries({ queryKey: ["api-keys", "trends"] });
}

export function useApiKeys() {
  const queryClient = useQueryClient();

  const apiKeysQuery = useQuery({
    queryKey: ["api-keys", "list"],
    queryFn: listApiKeys,
    select: (data) => data,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: ApiKeyCreateRequest) => createApiKey(payload),
    onSuccess: () => {
      toast.success("API 키를 생성했습니다");
      invalidateApiKeys(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message || "API 키를 생성하지 못했습니다");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ keyId, payload }: { keyId: string; payload: ApiKeyUpdateRequest }) =>
      updateApiKey(keyId, payload),
    onSuccess: () => {
      toast.success("API 키를 수정했습니다");
      invalidateApiKeys(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message || "API 키를 수정하지 못했습니다");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (keyId: string) => deleteApiKey(keyId),
    onSuccess: () => {
      toast.success("API 키를 삭제했습니다");
      invalidateApiKeys(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message || "API 키를 삭제하지 못했습니다");
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: (keyId: string) => regenerateApiKey(keyId),
    onSuccess: () => {
      toast.success("API 키를 재생성했습니다");
      invalidateApiKeys(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message || "API 키를 재생성하지 못했습니다");
    },
  });

  return {
    apiKeysQuery,
    createMutation,
    updateMutation,
    deleteMutation,
    regenerateMutation,
  };
}

export function useApiKeyTrends(keyId: string | null) {
  return useQuery({
    queryKey: ["api-keys", "trends", keyId],
    queryFn: () => getApiKeyTrends(keyId!),
    enabled: !!keyId,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    refetchIntervalInBackground: false,
  });
}

export function useApiKeyUsage7Day(keyId: string | null) {
  return useQuery({
    queryKey: ["api-keys", "usage-7d", keyId],
    queryFn: () => getApiKeyUsage7Day(keyId!),
    enabled: !!keyId,
    staleTime: 2 * 60_000,
    refetchInterval: 2 * 60_000,
    refetchIntervalInBackground: false,
  });
}
