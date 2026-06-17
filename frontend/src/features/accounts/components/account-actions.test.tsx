import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AccountActions } from "@/features/accounts/components/account-actions";
import type { AccountActionsProps } from "@/features/accounts/components/account-actions";
import { createAccountSummary } from "@/test/mocks/factories";

function renderAccountActions(
  overrides: Partial<AccountActionsProps> = {},
): AccountActionsProps {
  const props: AccountActionsProps = {
    account: createAccountSummary(),
    busy: false,
    onEditPlatform: vi.fn(),
    onPause: vi.fn(),
    onResume: vi.fn(),
    onProbe: vi.fn(),
    onDelete: vi.fn(),
    onReauth: vi.fn(),
    onExportAuth: vi.fn(),
    onSecurityWorkAuthorizedChange: vi.fn(),
    onLimitWarmupChange: vi.fn(),
    onRoutingPolicyChange: vi.fn(),
    ...overrides,
  };

  render(<AccountActions {...props} />);
  return props;
}

describe("AccountActions", () => {
  it("shows Edit for platform identities", async () => {
    const user = userEvent.setup();
    const account = createAccountSummary({
      accountId: "platform_1",
      email: "Platform Key",
      displayName: "Platform Key",
      label: "Platform Key",
      planType: "openai_platform",
      providerKind: "openai_platform",
      routingSubjectId: "platform_1",
      usage: null,
      auth: null,
    });
    const onEditPlatform = vi.fn();

    renderAccountActions({ account, onEditPlatform });

    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Re-authenticate" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(onEditPlatform).toHaveBeenCalledWith(account);
  });

  it("keeps Re-authenticate reserved for deactivated ChatGPT-web accounts", () => {
    renderAccountActions({
      account: createAccountSummary({
        accountId: "acc_chatgpt_1",
        email: "primary@example.com",
        displayName: "primary@example.com",
        providerKind: "chatgpt_web",
        status: "deactivated",
      }),
    });

    expect(screen.getByRole("button", { name: "Re-authenticate" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });

  it("renders an explicit routing policy selector", () => {
    renderAccountActions({
      account: createAccountSummary({ routingPolicy: "normal" }),
    });

    expect(screen.getByText("Routing policy")).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: "Routing policy" }),
    ).toHaveTextContent("Normal");
  });

  it("renders re-authenticate action for re-auth required accounts", () => {
    const onReauth = vi.fn();
    renderAccountActions({
      account: createAccountSummary({ status: "reauth_required" }),
      onReauth,
    });

    expect(
      screen.getByRole("button", { name: "Re-authenticate" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Pause" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("combobox", { name: "Routing policy" }),
    ).not.toBeInTheDocument();
  });

  it("fires the per-account probe callback for active accounts", async () => {
    const user = userEvent.setup();
    const account = createAccountSummary();
    const onProbe = vi.fn();

    renderAccountActions({ account, onProbe });

    await user.click(screen.getByRole("button", { name: "Force probe" }));

    expect(onProbe).toHaveBeenCalledWith(account.accountId);
    expect(onProbe).toHaveBeenCalledTimes(1);
  });

  it.each(["paused", "deactivated"] as const)(
    "disables force probe for %s accounts",
    async (status) => {
      const user = userEvent.setup();
      const onProbe = vi.fn();

      renderAccountActions({
        account: createAccountSummary({ status }),
        onProbe,
      });

      const button = screen.getByRole("button", { name: "Force probe" });
      expect(button).toBeDisabled();

      await user.click(button);

      expect(onProbe).not.toHaveBeenCalled();
    },
  );

  it("disables force probe in read-only mode", async () => {
    const user = userEvent.setup();
    const onProbe = vi.fn();

    renderAccountActions({
      readOnly: true,
      onProbe,
    });

    const button = screen.getByRole("button", { name: "Force probe" });
    expect(button).toBeDisabled();

    await user.click(button);

    expect(onProbe).not.toHaveBeenCalled();
  });
});
