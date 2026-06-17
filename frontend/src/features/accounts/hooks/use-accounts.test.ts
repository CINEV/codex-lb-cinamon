import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type PropsWithChildren } from "react";
import { describe, expect, it, vi } from "vitest";

import { useAccounts } from "@/features/accounts/hooks/use-accounts";
import { ApiError } from "@/lib/api-client";

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe("useAccounts", () => {
  it("loads accounts and invalidates related queries after mutations", async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useAccounts(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.accountsQuery.isSuccess).toBe(true));
    const firstAccountId = result.current.accountsQuery.data?.[0]?.accountId;
    expect(firstAccountId).toBeTruthy();

    await result.current.pauseMutation.mutateAsync(firstAccountId as string);
    await result.current.resumeMutation.mutateAsync(firstAccountId as string);
    const platformIdentity = await result.current.createPlatformMutation.mutateAsync({
      label: "Platform Key",
      apiKey: "sk-platform-test",
    });
    await result.current.updatePlatformMutation.mutateAsync({
      accountId: platformIdentity.accountId,
      payload: { label: "Platform Key Renamed" },
    });
    await result.current.probeMutation.mutateAsync({
      accountId: firstAccountId as string,
    });
    const routingPolicyResult = await result.current.routingPolicyMutation.mutateAsync({
      accountId: firstAccountId as string,
      routingPolicy: "preserve",
    });
    expect(routingPolicyResult.routingPolicy).toBe("preserve");

    const imported = await result.current.importMutation.mutateAsync(
      new File(["{}"], "auth.json", { type: "application/json" }),
    );
    await result.current.deleteMutation.mutateAsync({
      accountId: imported.accountId,
      deleteHistory: false,
    });

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["accounts", "list"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["accounts", "trends"] });
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["accounts", "trends", firstAccountId],
      });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["dashboard", "overview"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["dashboard", "projections"] });
    });
  });

  it("exports auth for an account without invalidating account queries", async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useAccounts(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.accountsQuery.isSuccess).toBe(true));
    const firstAccountId = result.current.accountsQuery.data?.[0]?.accountId;
    expect(firstAccountId).toBeTruthy();

    await result.current.exportAuthMutation.mutateAsync(firstAccountId as string);

    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ["accounts", "list"] });
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ["accounts", "trends"] });
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ["dashboard", "overview"] });
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ["dashboard", "projections"] });
  });

  it("surfaces platform identity conflict errors", async () => {
    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useAccounts(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.accountsQuery.isSuccess).toBe(true));

    await result.current.createPlatformMutation.mutateAsync({
      label: "Platform Key",
      apiKey: "sk-platform-test",
    });

    await expect(
      result.current.createPlatformMutation.mutateAsync({
        label: "Second Platform Key",
        apiKey: "sk-platform-test-2",
      }),
    ).rejects.toMatchObject({
      code: "platform_identity_conflict",
      message: "Only one OpenAI Platform fallback key can be registered.",
    } satisfies Partial<ApiError>);
  });

  it("surfaces platform identity prerequisite errors", async () => {
    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useAccounts(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.accountsQuery.isSuccess).toBe(true));
    const activeChatgptAccountId = result.current.accountsQuery.data?.find(
      (account) => account.providerKind !== "openai_platform" && account.status === "active",
    )?.accountId;

    expect(activeChatgptAccountId).toBeTruthy();

    await result.current.pauseMutation.mutateAsync(activeChatgptAccountId as string);

    await expect(
      result.current.createPlatformMutation.mutateAsync({
        label: "Platform Without Primary",
        apiKey: "sk-platform-test",
      }),
    ).rejects.toMatchObject({
      code: "platform_identity_prerequisite_failed",
      message: "OpenAI Platform fallback requires at least one active ChatGPT-web account.",
    } satisfies Partial<ApiError>);
  });
});
