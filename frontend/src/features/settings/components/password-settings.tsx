import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AlertMessage } from "@/components/alert-message";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { changePassword, removePassword, setupPassword } from "@/features/auth/api";
import { useAuthStore } from "@/features/auth/hooks/use-auth";
import {
  PasswordChangeRequestSchema,
  PasswordRemoveRequestSchema,
  PasswordSetupRequestSchema,
} from "@/features/auth/schemas";
import { getErrorMessage } from "@/utils/errors";

type PasswordDialog = "setup" | "change" | "remove" | null;

export type PasswordSettingsProps = {
  disabled?: boolean;
};

export function PasswordSettings({ disabled = false }: PasswordSettingsProps) {
  const passwordRequired = useAuthStore((s) => s.passwordRequired);
  const bootstrapRequired = useAuthStore((s) => s.bootstrapRequired);
  const bootstrapTokenConfigured = useAuthStore((s) => s.bootstrapTokenConfigured);
  const refreshSession = useAuthStore((s) => s.refreshSession);

  const [activeDialog, setActiveDialog] = useState<PasswordDialog>(null);
  const [error, setError] = useState<string | null>(null);

  const setupForm = useForm({
    resolver: zodResolver(PasswordSetupRequestSchema),
    defaultValues: { password: "", bootstrapToken: "" },
  });

  const changeForm = useForm({
    resolver: zodResolver(PasswordChangeRequestSchema),
    defaultValues: { currentPassword: "", newPassword: "" },
  });

  const removeForm = useForm({
    resolver: zodResolver(PasswordRemoveRequestSchema),
    defaultValues: { password: "" },
  });

  const busy =
    setupForm.formState.isSubmitting ||
    changeForm.formState.isSubmitting ||
    removeForm.formState.isSubmitting;
  const lock = busy || disabled;

  const closeDialog = () => {
    setActiveDialog(null);
    setError(null);
    setupForm.reset();
    changeForm.reset();
    removeForm.reset();
  };

  const handleSetup = async (values: { password: string; bootstrapToken?: string }) => {
    setError(null);
    try {
      await setupPassword({
        password: values.password,
        bootstrapToken: values.bootstrapToken?.trim() ? values.bootstrapToken.trim() : undefined,
      });
      await refreshSession();
      toast.success("비밀번호를 설정했습니다");
      closeDialog();
    } catch (caught) {
      setError(getErrorMessage(caught));
    }
  };

  const handleChange = async (values: { currentPassword: string; newPassword: string }) => {
    setError(null);
    try {
      await changePassword(values);
      toast.success("비밀번호를 변경했습니다");
      closeDialog();
    } catch (caught) {
      setError(getErrorMessage(caught));
    }
  };

  const handleRemove = async (values: { password: string }) => {
    setError(null);
    try {
      await removePassword(values);
      await refreshSession();
      toast.success("비밀번호를 제거했습니다");
      closeDialog();
    } catch (caught) {
      setError(getErrorMessage(caught));
    }
  };

  return (
    <section className="rounded-xl border bg-card p-5">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <KeyRound className="h-4 w-4 text-primary" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">비밀번호</h3>
            <p className="text-xs text-muted-foreground">
              {passwordRequired ? "비밀번호가 설정되어 있습니다." : "설정된 비밀번호가 없습니다."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {passwordRequired ? (
            <>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-8 text-xs"
                disabled={lock}
                onClick={() => setActiveDialog("change")}
              >
                변경
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-8 text-xs text-destructive hover:text-destructive"
                disabled={lock}
                onClick={() => setActiveDialog("remove")}
              >
                제거
              </Button>
            </>
          ) : (
            <Button
              type="button"
              size="sm"
              className="h-8 text-xs"
              disabled={lock}
              onClick={() => setActiveDialog("setup")}
            >
              비밀번호 설정
            </Button>
          )}
        </div>
        </div>
      </div>

      {/* Setup dialog */}
      <Dialog open={activeDialog === "setup"} onOpenChange={(open) => !open && closeDialog()}>
        <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>비밀번호 설정</DialogTitle>
              <DialogDescription>대시보드 로그인용 비밀번호를 설정합니다.</DialogDescription>
            </DialogHeader>
            {bootstrapRequired ? (
              <AlertMessage variant="error">
                {bootstrapTokenConfigured
                  ? "원격 설정에는 대시보드 부트스트랩 토큰이 필요합니다."
                  : "서버에 대시보드 부트스트랩 토큰이 설정되기 전까지 원격 설정은 차단됩니다."}
              </AlertMessage>
            ) : null}
            {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}
            <Form {...setupForm}>
              <form onSubmit={setupForm.handleSubmit(handleSetup)} className="space-y-4">
              <FormField
                control={setupForm.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>비밀번호</FormLabel>
                    <FormControl>
                      <Input {...field} type="password" autoComplete="new-password" placeholder="최소 8자" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
                />
                {bootstrapRequired ? (
                  <FormField
                    control={setupForm.control}
                    name="bootstrapToken"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>부트스트랩 토큰</FormLabel>
                        <FormControl>
                          <Input {...field} type="password" autoComplete="one-time-code" placeholder="부트스트랩 토큰 입력" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                ) : null}
                <DialogFooter>
                <Button type="button" variant="outline" onClick={closeDialog} disabled={busy}>
                  취소
                </Button>
                <Button type="submit" disabled={lock}>
                  비밀번호 설정
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Change dialog */}
      <Dialog open={activeDialog === "change"} onOpenChange={(open) => !open && closeDialog()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>비밀번호 변경</DialogTitle>
            <DialogDescription>현재 비밀번호와 새 비밀번호를 입력하세요.</DialogDescription>
          </DialogHeader>
          {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}
          <Form {...changeForm}>
            <form onSubmit={changeForm.handleSubmit(handleChange)} className="space-y-4">
              <FormField
                control={changeForm.control}
                name="currentPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>현재 비밀번호</FormLabel>
                    <FormControl>
                      <Input {...field} type="password" autoComplete="current-password" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={changeForm.control}
                name="newPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>새 비밀번호</FormLabel>
                    <FormControl>
                      <Input {...field} type="password" autoComplete="new-password" placeholder="최소 8자" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={closeDialog} disabled={busy}>
                  취소
                </Button>
                <Button type="submit" disabled={lock}>
                  비밀번호 변경
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Remove dialog */}
      <Dialog open={activeDialog === "remove"} onOpenChange={(open) => !open && closeDialog()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>비밀번호 제거</DialogTitle>
            <DialogDescription>현재 비밀번호를 입력해 제거를 확인하세요.</DialogDescription>
          </DialogHeader>
          {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}
          <Form {...removeForm}>
            <form onSubmit={removeForm.handleSubmit(handleRemove)} className="space-y-4">
              <FormField
                control={removeForm.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>현재 비밀번호</FormLabel>
                    <FormControl>
                      <Input {...field} type="password" autoComplete="current-password" placeholder="현재 비밀번호 입력" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={closeDialog} disabled={busy}>
                  취소
                </Button>
                <Button type="submit" variant="destructive" disabled={lock}>
                  비밀번호 제거
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </section>
  );
}
