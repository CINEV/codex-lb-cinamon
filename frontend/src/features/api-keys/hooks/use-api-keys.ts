import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  createApiKey,
  deleteApiKey,
  listApiKeys,
  regenerateApiKey,
  updateApiKey,
} from "@/features/api-keys/api";
import type {
  ApiKeyCreateRequest,
  ApiKeyUpdateRequest,
} from "@/features/api-keys/schemas";

export function useApiKeys() {
  const queryClient = useQueryClient();

  const apiKeysQuery = useQuery({
    queryKey: ["api-keys", "list"],
    queryFn: listApiKeys,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["api-keys", "list"] });
  };

  const createMutation = useMutation({
    mutationFn: (payload: ApiKeyCreateRequest) => createApiKey(payload),
    onSuccess: () => {
      toast.success("API 키를 생성했습니다");
      invalidate();
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
      invalidate();
    },
    onError: (error: Error) => {
      toast.error(error.message || "API 키를 수정하지 못했습니다");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (keyId: string) => deleteApiKey(keyId),
    onSuccess: () => {
      toast.success("API 키를 삭제했습니다");
      invalidate();
    },
    onError: (error: Error) => {
      toast.error(error.message || "API 키를 삭제하지 못했습니다");
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: (keyId: string) => regenerateApiKey(keyId),
    onSuccess: () => {
      toast.success("API 키를 재생성했습니다");
      invalidate();
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
