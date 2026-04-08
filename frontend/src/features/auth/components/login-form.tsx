import { zodResolver } from "@hookform/resolvers/zod";
import { Lock } from "lucide-react";
import { useForm } from "react-hook-form";

import { AlertMessage } from "@/components/alert-message";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { LoginRequestSchema } from "@/features/auth/schemas";
import { useAuthStore } from "@/features/auth/hooks/use-auth";

export function LoginForm() {
  const login = useAuthStore((state) => state.login);
  const loading = useAuthStore((state) => state.loading);
  const error = useAuthStore((state) => state.error);
  const clearError = useAuthStore((state) => state.clearError);

  const form = useForm({
    resolver: zodResolver(LoginRequestSchema),
    defaultValues: { password: "" },
  });

  const handleSubmit = async (values: { password: string }) => {
    clearError();
    await login(values.password);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="rounded-2xl border bg-card p-6 shadow-[var(--shadow-md)]">
        <div className="space-y-1.5">
          <h2 className="text-base font-semibold tracking-tight">로그인</h2>
          <p className="text-sm text-muted-foreground">계속하려면 관리자 비밀번호를 입력하세요.</p>
        </div>

        <div className="mt-5">
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-xs font-medium">비밀번호</FormLabel>
                <div className="relative">
                  <Lock className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground/60" aria-hidden="true" />
                  <FormControl>
                    <Input
                      {...field}
                      type="password"
                      autoComplete="current-password"
                      placeholder="비밀번호 입력"
                      disabled={loading}
                      className="pl-9"
                    />
                  </FormControl>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {error ? <AlertMessage variant="error" className="mt-4">{error}</AlertMessage> : null}

        <Button type="submit" className="press-scale mt-5 w-full" disabled={loading}>
          {loading ? <Spinner size="sm" className="mr-2" /> : null}
          로그인
        </Button>
      </form>
    </Form>
  );
}
