import { CodexLogo } from "@/components/brand/codex-logo";
import { AlertMessage } from "@/components/alert-message";
import { PasswordSettings } from "@/features/settings/components/password-settings";
import { useAuthStore } from "@/features/auth/hooks/use-auth";

export function BootstrapSetupScreen() {
  const bootstrapTokenConfigured = useAuthStore((state) => state.bootstrapTokenConfigured);

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/4 -right-1/4 h-[600px] w-[600px] rounded-full bg-primary/5 blur-3xl" />
        <div className="absolute -bottom-1/4 -left-1/4 h-[500px] w-[500px] rounded-full bg-primary/3 blur-3xl" />
        <div className="absolute bottom-0 left-1/2 h-[400px] w-[400px] -translate-x-1/2 rounded-full bg-primary/4 blur-3xl" />
      </div>

      <div className="relative w-full max-w-2xl space-y-6 animate-fade-in-up">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 shadow-sm ring-2 ring-primary/10 ring-offset-2 ring-offset-background">
            <CodexLogo size={28} className="text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">원격 설정 완료</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              관리자 비밀번호가 설정되기 전까지 원격 대시보드 접근은 잠겨 있습니다.
            </p>
          </div>
        </div>

        <div className="rounded-2xl border bg-card p-6 shadow-[var(--shadow-md)]">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              아래 비밀번호 설정 절차를 완료해야 나머지 관리자 UI를 사용할 수 있습니다.
            </p>
            <AlertMessage variant="error">
              {bootstrapTokenConfigured
                ? "초기 비밀번호를 설정할 때 대시보드 부트스트랩 토큰을 입력하세요."
                : "서버에 CODEX_LB_DASHBOARD_BOOTSTRAP_TOKEN이 설정되기 전까지 원격 설정은 차단됩니다."}
            </AlertMessage>
          </div>
        </div>

        <PasswordSettings />
      </div>
    </div>
  );
}
