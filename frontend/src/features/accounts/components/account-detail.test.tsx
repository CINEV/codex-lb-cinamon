import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AccountDetail } from "@/features/accounts/components/account-detail";
import { createAccountSummary } from "@/test/mocks/factories";

function renderAccountDetail(account = createAccountSummary()) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AccountDetail
        account={account}
        busy={false}
        onEditPlatform={() => {}}
        onPause={() => {}}
        onResume={() => {}}
        onSetAlias={async () => undefined}
        onDelete={() => {}}
        onReauth={() => {}}
        onExport={() => {}}
        onLimitWarmupChange={() => {}}
      />
    </QueryClientProvider>,
  );
}

describe("AccountDetail", () => {
  it("hides alias form for platform identities", () => {
    renderAccountDetail(
      createAccountSummary({
        accountId: "platform_1",
        email: "Platform Key",
        displayName: "Platform Key",
        planType: "openai_platform",
        providerKind: "openai_platform",
        routingSubjectId: "platform_1",
        usage: null,
        auth: null,
      }),
    );

    expect(screen.queryByLabelText("Account alias")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save alias" })).not.toBeInTheDocument();
  });

  it("keeps alias form for ChatGPT-web accounts", () => {
    renderAccountDetail();

    expect(screen.getByLabelText("Account alias")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save alias" })).toBeInTheDocument();
  });
});
