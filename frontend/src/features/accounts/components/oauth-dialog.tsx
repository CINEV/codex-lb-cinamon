import { Check, CircleAlert, Copy, ExternalLink, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import type { OAuthState } from "@/features/accounts/schemas";
import { formatCountdown } from "@/utils/formatters";

type Stage = "intro" | "browser" | "device" | "success" | "error";

function getStage(state: OAuthState): Stage {
  if (state.status === "success") return "success";
  if (state.status === "error") return "error";
  if (state.method === "browser" && (state.status === "pending" || state.status === "starting")) return "browser";
  if (state.method === "device" && (state.status === "pending" || state.status === "starting")) return "device";
  return "intro";
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [text]);

  return (
    <Button
      type="button"
      size="sm"
      variant="ghost"
      className="h-7 cursor-pointer gap-1 px-2 text-xs disabled:cursor-not-allowed"
      onClick={() => void handleCopy()}
    >
      {copied ? (
        <>
          <Check className="h-3 w-3" />
          복사됨!
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          복사
        </>
      )}
    </Button>
  );
}

function ManualCallbackInput({
  onSubmit,
  disabled = false,
}: {
  onSubmit: (callbackUrl: string) => Promise<void>;
  disabled?: boolean;
}) {
  const [callbackUrl, setCallbackUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (disabled) {
      setCallbackUrl("");
    }
  }, [disabled]);

  const handleSubmit = useCallback(async () => {
    if (!callbackUrl.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(callbackUrl.trim());
      setCallbackUrl("");
    } catch {
      // Parent state renders the error stage/message.
    } finally {
      setSubmitting(false);
    }
  }, [callbackUrl, onSubmit]);

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground">
        콜백 URL 붙여넣기(원격 서버용)
      </p>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={callbackUrl}
          onChange={(e) => setCallbackUrl(e.target.value)}
          disabled={disabled}
          placeholder="http://localhost:1455/auth/callback?code=...&state=..."
          className="flex-1 rounded-lg border bg-muted/20 px-3 py-2 font-mono text-xs outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
        />
        <Button
          type="button"
          size="sm"
          className="h-8 cursor-pointer px-3 text-xs disabled:cursor-not-allowed"
          disabled={disabled || !callbackUrl.trim() || submitting}
          onClick={() => void handleSubmit()}
        >
          {submitting ? "제출 중..." : "제출"}
        </Button>
      </div>
    </div>
  );
}

export type OauthDialogProps = {
  open: boolean;
  state: OAuthState;
  onOpenChange: (open: boolean) => void;
  onStart: (method?: "browser" | "device") => Promise<void>;
  onComplete: () => Promise<void>;
  onManualCallback: (callbackUrl: string) => Promise<void>;
  onReset: () => void;
};

export function OauthDialog({
  open,
  state,
  onOpenChange,
  onStart,
  onComplete,
  onManualCallback,
  onReset,
}: OauthDialogProps) {
  const [selectedMethod, setSelectedMethod] = useState<"browser" | "device">("browser");
  const stage = getStage(state);
  const completedRef = useRef(false);
  const browserRefreshInProgress = stage === "browser" && state.status === "starting";

  useEffect(() => {
    if (stage === "success" && !completedRef.current) {
      completedRef.current = true;
      void onComplete();
    }
    if (stage === "intro") {
      completedRef.current = false;
    }
  }, [stage, onComplete]);

  const close = (next: boolean) => {
    onOpenChange(next);
    if (!next) {
      onReset();
      setSelectedMethod("browser");
    }
  };

  const handleStart = () => {
    void onStart(selectedMethod);
  };

  const handleRefreshBrowserLink = () => {
    void onStart("browser");
  };

  const handleChangeMethod = () => {
    onReset();
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {stage === "success" ? "계정 추가 완료" : stage === "error" ? "인증 실패" : "OAuth로 계정 추가"}
          </DialogTitle>
          {stage === "intro" ? (
            <DialogDescription>로그인 방식을 선택하고 인증을 완료하세요.</DialogDescription>
          ) : null}
        </DialogHeader>

        {/* Intro stage */}
        {stage === "intro" ? (
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setSelectedMethod("browser")}
              className={cn(
                "w-full cursor-pointer rounded-lg border p-3 text-left transition-colors",
                selectedMethod === "browser"
                  ? "border-primary bg-primary/5"
                  : "hover:bg-muted/50",
              )}
            >
              <p className="text-sm font-medium">브라우저(PKCE)</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                브라우저 창을 열어 로그인합니다. 대부분의 사용자에게 권장됩니다.
              </p>
            </button>
            <button
              type="button"
              onClick={() => setSelectedMethod("device")}
              className={cn(
                "w-full cursor-pointer rounded-lg border p-3 text-left transition-colors",
                selectedMethod === "device"
                  ? "border-primary bg-primary/5"
                  : "hover:bg-muted/50",
              )}
            >
              <p className="text-sm font-medium">디바이스 코드</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                다른 기기에서 코드를 입력해 로그인합니다. 헤드리스 환경에 유용합니다.
              </p>
            </button>
          </div>
        ) : null}

        {/* Browser stage */}
        {stage === "browser" ? (
          <div className="min-w-0 space-y-3 text-sm">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium text-muted-foreground">인증 URL</p>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-7 cursor-pointer gap-1 px-2 text-xs disabled:cursor-not-allowed"
                  disabled={browserRefreshInProgress}
                  onClick={handleRefreshBrowserLink}
                >
                  {browserRefreshInProgress ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin" />
                      새로 고침 중...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="h-3 w-3" />
                      링크 새로 고침
                    </>
                  )}
                </Button>
              </div>
              {browserRefreshInProgress ? (
                <div className="flex items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>새 로그인 링크를 생성하는 중...</span>
                </div>
              ) : state.authorizationUrl ? (
                <div className="flex min-w-0 items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2">
                  <p className="min-w-0 flex-1 truncate font-mono text-xs">{state.authorizationUrl}</p>
                  <CopyButton text={state.authorizationUrl} />
                </div>
              ) : null}
              <p className="text-xs text-muted-foreground">
                현재 로그인 페이지를 이미 사용했다면 링크를 새로 고치세요.
              </p>
            </div>
            <ManualCallbackInput onSubmit={onManualCallback} disabled={browserRefreshInProgress} />
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>인증 완료를 기다리는 중...</span>
            </div>
          </div>
        ) : null}

        {/* Device stage */}
        {stage === "device" ? (
          <div className="space-y-3 text-sm">
            <ol className="list-inside list-decimal space-y-1 text-xs text-muted-foreground">
              <li>아래 인증 링크를 엽니다</li>
              <li>안내가 나오면 사용자 코드를 입력합니다</li>
              <li>해당 페이지에서 로그인을 완료합니다</li>
            </ol>

            {state.userCode ? (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">사용자 코드</p>
                <div className="flex items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2">
                  <p className="min-w-0 flex-1 font-mono text-lg font-bold tracking-widest">{state.userCode}</p>
                  <CopyButton text={state.userCode} />
                </div>
              </div>
            ) : null}

            {state.verificationUrl ? (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">인증 URL</p>
                <div className="flex min-w-0 items-center gap-2 overflow-hidden rounded-lg border bg-muted/20 px-3 py-2">
                  <p className="min-w-0 flex-1 truncate break-all font-mono text-xs">{state.verificationUrl}</p>
                  <CopyButton text={state.verificationUrl} />
                </div>
              </div>
            ) : null}

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>
                인증 대기 중
                {state.expiresInSeconds != null && state.expiresInSeconds > 0
                  ? ` · ${formatCountdown(state.expiresInSeconds)} 후 만료`
                  : "..."}
              </span>
            </div>
          </div>
        ) : null}

        {/* Success stage */}
        {stage === "success" ? (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-3 text-sm text-emerald-700 dark:text-emerald-400">
            <Check className="h-4 w-4 shrink-0" />
            <p>계정이 성공적으로 추가되었습니다.</p>
          </div>
        ) : null}

        {/* Error stage */}
        {stage === "error" ? (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-3 text-sm text-destructive">
            <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{state.errorMessage || "알 수 없는 오류가 발생했습니다."}</p>
          </div>
        ) : null}

        <DialogFooter>
          {stage === "intro" ? (
            <>
              <Button
                type="button"
                variant="outline"
                className="cursor-pointer disabled:cursor-not-allowed"
                onClick={() => close(false)}
              >
                취소
              </Button>
              <Button
                type="button"
                className="cursor-pointer disabled:cursor-not-allowed"
                onClick={handleStart}
              >
                로그인 시작
              </Button>
            </>
          ) : null}

          {stage === "browser" ? (
            <>
              <Button
                type="button"
                variant="outline"
                className="cursor-pointer disabled:cursor-not-allowed"
                disabled={browserRefreshInProgress}
                onClick={handleChangeMethod}
              >
                방식 변경
              </Button>
              {state.authorizationUrl && !browserRefreshInProgress ? (
                <Button
                  type="button"
                  className="cursor-pointer disabled:cursor-not-allowed"
                  asChild
                >
                  <a href={state.authorizationUrl} target="_blank" rel="noreferrer">
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    로그인 페이지 열기
                  </a>
                </Button>
              ) : null}
            </>
          ) : null}

          {stage === "device" ? (
            <>
              <Button
                type="button"
                variant="outline"
                className="cursor-pointer disabled:cursor-not-allowed"
                onClick={handleChangeMethod}
              >
                방식 변경
              </Button>
              {state.verificationUrl ? (
                <Button
                  type="button"
                  className="cursor-pointer disabled:cursor-not-allowed"
                  asChild
                >
                  <a href={state.verificationUrl} target="_blank" rel="noreferrer">
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    링크 열기
                  </a>
                </Button>
              ) : null}
            </>
          ) : null}

          {stage === "success" ? (
            <Button
              type="button"
              className="cursor-pointer disabled:cursor-not-allowed"
              onClick={() => close(false)}
            >
              완료
            </Button>
          ) : null}

          {stage === "error" ? (
            <>
              <Button
                type="button"
                variant="outline"
                className="cursor-pointer disabled:cursor-not-allowed"
                onClick={handleChangeMethod}
              >
                다시 시도
              </Button>
              <Button
                type="button"
                className="cursor-pointer disabled:cursor-not-allowed"
                onClick={() => close(false)}
              >
                닫기
              </Button>
            </>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
