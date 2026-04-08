import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getSettings, updateSettings } from "@/features/settings/api";
import type { SettingsUpdateRequest } from "@/features/settings/schemas";

export function useSettings() {
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ["settings", "detail"],
    queryFn: getSettings,
  });

  const updateSettingsMutation = useMutation({
    mutationFn: (payload: SettingsUpdateRequest) => updateSettings(payload),
    onSuccess: () => {
      toast.success("설정을 저장했습니다");
      void queryClient.invalidateQueries({ queryKey: ["settings", "detail"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "설정을 저장하지 못했습니다");
    },
  });

  return {
    settingsQuery,
    updateSettingsMutation,
  };
}
