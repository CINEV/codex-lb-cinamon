import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  PLATFORM_ROUTE_FAMILY_ORDER,
  PLATFORM_ROUTE_OPTIONS,
  shouldIncludeRouteFamily,
  type CheckedState,
} from "@/features/accounts/components/platform-identity-route-options";
import type {
  AccountSummary,
  PlatformIdentityCreateRequest,
  PlatformIdentityUpdateRequest,
  PlatformRouteFamily,
} from "@/features/accounts/schemas";

function normalizeOptionalText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeEligibleRouteFamilies(value: PlatformRouteFamily[]): PlatformRouteFamily[] {
  const next = new Set(value);
  return PLATFORM_ROUTE_FAMILY_ORDER.filter((routeFamily) => next.has(routeFamily));
}

function areRouteFamiliesEqual(left: PlatformRouteFamily[], right: PlatformRouteFamily[]): boolean {
  if (left.length !== right.length) {
    return false;
  }
  return left.every((value, index) => value === right[index]);
}

type PlatformIdentityFormState = {
  label: string;
  apiKey: string;
  organization: string;
  project: string;
  eligibleRouteFamilies: PlatformRouteFamily[];
};

function createPlatformIdentityFormState({
  isEdit,
  label,
  organization,
  project,
  eligibleRouteFamilies,
}: {
  isEdit: boolean;
  label: string;
  organization: string | null;
  project: string | null;
  eligibleRouteFamilies: PlatformRouteFamily[];
}): PlatformIdentityFormState {
  if (!isEdit) {
    return {
      label: "",
      apiKey: "",
      organization: "",
      project: "",
      eligibleRouteFamilies: [],
    };
  }
  return {
    label,
    apiKey: "",
    organization: organization ?? "",
    project: project ?? "",
    eligibleRouteFamilies,
  };
}

export type PlatformIdentityDialogProps = {
  open: boolean;
  busy: boolean;
  error: string | null;
  mode?: "create" | "edit";
  account?: AccountSummary | null;
  prerequisiteSatisfied?: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (
    payload: PlatformIdentityCreateRequest | PlatformIdentityUpdateRequest,
  ) => Promise<void>;
};

export function PlatformIdentityDialog({
  open,
  busy,
  error,
  mode = "create",
  account = null,
  prerequisiteSatisfied = true,
  onOpenChange,
  onSubmit,
}: PlatformIdentityDialogProps) {
  const isEdit = mode === "edit";
  const initialLabel = account ? account.label ?? account.displayName ?? account.email : "";
  const initialOrganization = account?.organization ?? null;
  const initialProject = account?.project ?? null;
  const initialEligibleRouteFamilies = useMemo(
    () => normalizeEligibleRouteFamilies(account?.eligibleRouteFamilies ?? []),
    [account?.eligibleRouteFamilies],
  );

  const handleOpenChange = (nextOpen: boolean) => {
    onOpenChange(nextOpen);
  };

  const formKey = [
    mode,
    account?.accountId ?? "create",
    initialLabel,
    initialOrganization ?? "",
    initialProject ?? "",
    initialEligibleRouteFamilies.join(","),
  ].join(":");

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "OpenAI Platform API 키 수정" : "OpenAI Platform API 키 추가"}</DialogTitle>
          <DialogDescription>
            {isEdit ? (
              <>
                <code>/v1/models</code>와 상태 없는 HTTP <code>/v1/responses</code>에만 쓰이는 폴백 전용 업스트림
                ID를 수정합니다. ChatGPT 계정은 계속 기본 경로로 유지되고, 이 키는 기본 또는 보조 사용량 임계치 때문에
                호환 가능한 ChatGPT 풀이 비정상일 때만 사용됩니다.
              </>
            ) : (
              <>
                <code>/v1/models</code>와 상태 없는 HTTP <code>/v1/responses</code>에만 쓰이는 폴백 전용 업스트림
                ID를 등록합니다. ChatGPT 계정은 계속 기본 경로로 유지되고, 이 키는 기본 또는 보조 사용량 임계치 때문에
                호환 가능한 ChatGPT 풀이 비정상일 때만 사용됩니다.
              </>
            )}
          </DialogDescription>
        </DialogHeader>
        {open ? (
          <PlatformIdentityDialogForm
            key={formKey}
            busy={busy}
            error={error}
            mode={mode}
            account={account}
            prerequisiteSatisfied={prerequisiteSatisfied}
            initialLabel={initialLabel}
            initialOrganization={initialOrganization}
            initialProject={initialProject}
            initialEligibleRouteFamilies={initialEligibleRouteFamilies}
            onOpenChange={onOpenChange}
            onSubmit={onSubmit}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

type PlatformIdentityDialogFormProps = {
  busy: boolean;
  error: string | null;
  mode: "create" | "edit";
  account: AccountSummary | null;
  prerequisiteSatisfied: boolean;
  initialLabel: string;
  initialOrganization: string | null;
  initialProject: string | null;
  initialEligibleRouteFamilies: PlatformRouteFamily[];
  onOpenChange: (open: boolean) => void;
  onSubmit: (
    payload: PlatformIdentityCreateRequest | PlatformIdentityUpdateRequest,
  ) => Promise<void>;
};

function PlatformIdentityDialogForm({
  busy,
  error,
  mode,
  account,
  prerequisiteSatisfied,
  initialLabel,
  initialOrganization,
  initialProject,
  initialEligibleRouteFamilies,
  onOpenChange,
  onSubmit,
}: PlatformIdentityDialogFormProps) {
  const isEdit = mode === "edit";
  const [formState, setFormState] = useState(() =>
    createPlatformIdentityFormState({
      isEdit,
      label: initialLabel,
      organization: initialOrganization,
      project: initialProject,
      eligibleRouteFamilies: initialEligibleRouteFamilies,
    }),
  );
  const { label, apiKey, organization, project, eligibleRouteFamilies } = formState;

  const resetForm = () => {
    setFormState(
      createPlatformIdentityFormState({
        isEdit,
        label: initialLabel,
        organization: initialOrganization,
        project: initialProject,
        eligibleRouteFamilies: initialEligibleRouteFamilies,
      }),
    );
  };

  const hasChanges = useMemo(() => {
    if (!isEdit || !account) {
      return true;
    }
    const nextLabel = label.trim();
    const nextOrganization = normalizeOptionalText(organization);
    const nextProject = normalizeOptionalText(project);
    const nextEligibleRouteFamilies = normalizeEligibleRouteFamilies(eligibleRouteFamilies);
    return (
      nextLabel !== initialLabel ||
      apiKey.trim().length > 0 ||
      nextOrganization !== initialOrganization ||
      nextProject !== initialProject ||
      !areRouteFamiliesEqual(nextEligibleRouteFamilies, initialEligibleRouteFamilies)
    );
  }, [
    account,
    apiKey,
    eligibleRouteFamilies,
    initialEligibleRouteFamilies,
    initialLabel,
    initialOrganization,
    initialProject,
    isEdit,
    label,
    organization,
    project,
  ]);

  const canSubmit = useMemo(
    () =>
      label.trim().length > 0 &&
      (isEdit ? !!account && hasChanges : prerequisiteSatisfied && apiKey.trim().length > 0),
    [account, apiKey, hasChanges, isEdit, label, prerequisiteSatisfied],
  );

  const updateFormState = <Key extends keyof PlatformIdentityFormState>(
    key: Key,
    value: PlatformIdentityFormState[Key],
  ) => {
    setFormState((current) => ({ ...current, [key]: value }));
  };

  const handleRouteToggle = (routeFamily: PlatformRouteFamily, checked: CheckedState) => {
    setFormState((current) => {
      const next = new Set(current.eligibleRouteFamilies);
      if (shouldIncludeRouteFamily(checked)) {
        next.add(routeFamily);
      } else {
        next.delete(routeFamily);
      }
      return {
        ...current,
        eligibleRouteFamilies: PLATFORM_ROUTE_FAMILY_ORDER.filter((value) => next.has(value)),
      };
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    if (isEdit) {
      const payload: PlatformIdentityUpdateRequest = {};
      const nextLabel = label.trim();
      const nextOrganization = normalizeOptionalText(organization);
      const nextProject = normalizeOptionalText(project);
      const nextEligibleRouteFamilies = normalizeEligibleRouteFamilies(eligibleRouteFamilies);

      if (nextLabel !== initialLabel) {
        payload.label = nextLabel;
      }
      if (apiKey.trim().length > 0) {
        payload.apiKey = apiKey.trim();
      }
      if (nextOrganization !== initialOrganization) {
        payload.organization = nextOrganization;
      }
      if (nextProject !== initialProject) {
        payload.project = nextProject;
      }
      if (!areRouteFamiliesEqual(nextEligibleRouteFamilies, initialEligibleRouteFamilies)) {
        payload.eligibleRouteFamilies = nextEligibleRouteFamilies;
      }
      await onSubmit(payload);
    } else {
      await onSubmit({
        label,
        apiKey,
        organization,
        project,
        eligibleRouteFamilies,
      });
    }
    resetForm();
    onOpenChange(false);
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <Label htmlFor="platform-label">레이블</Label>
        <Input
          id="platform-label"
          placeholder="운영용 플랫폼 키"
          value={label}
          onChange={(event) => updateFormState("label", event.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="platform-api-key">API 키</Label>
        <Input
          id="platform-api-key"
          type="password"
          placeholder={isEdit ? "비워두면 기존 키를 유지합니다" : "sk-..."}
          value={apiKey}
          onChange={(event) => updateFormState("apiKey", event.target.value)}
        />
        {isEdit ? (
          <p className="text-xs text-muted-foreground">
            현재 Platform API 키를 유지하려면 비워두세요. 자격 증명을 교체할 때만 새 키를 입력하세요.
          </p>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="platform-organization">조직</Label>
          <Input
            id="platform-organization"
            placeholder="org_..."
            value={organization}
            onChange={(event) => updateFormState("organization", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="platform-project">프로젝트</Label>
          <Input
            id="platform-project"
            placeholder="proj_..."
            value={project}
            onChange={(event) => updateFormState("project", event.target.value)}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>허용 라우트</Label>
        <div className="space-y-2 rounded-lg border bg-muted/20 p-3">
          {PLATFORM_ROUTE_OPTIONS.map((option) => (
            <label key={option.value} className="flex items-start gap-3 rounded-md px-1 py-1.5">
              <Checkbox
                checked={eligibleRouteFamilies.includes(option.value)}
                onCheckedChange={(checked) => handleRouteToggle(option.value, checked)}
              />
              <span className="min-w-0">
                <span className="block text-sm font-medium">{option.label}</span>
                <span className="block text-xs text-muted-foreground">
                  {option.description}
                  {option.value === "public_responses_http"
                    ? " 상태 없는 HTTP 전용이며, compact, chat completions, websocket, 연속성 의존 요청은 계속 ChatGPT로 보냅니다."
                    : ""}
                </span>
              </span>
            </label>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          {eligibleRouteFamilies.length === 0
            ? "허용된 라우트 패밀리가 없습니다. 하나 이상 선택하기 전까지 이 ID는 라우팅되지 않습니다."
            : `${eligibleRouteFamilies.length}개의 라우트 패밀리에서 사용할 수 있습니다.`}
        </p>
        <p className="text-xs text-muted-foreground">
          {isEdit
            ? "이 키는 /v1/models와 상태 없는 HTTP /v1/responses에서만 사용할 수 있습니다. ChatGPT 전용, compact, websocket, 연속성 의존 요청은 계속 ChatGPT에 남습니다."
            : "일시 중지되거나 비활성화되지 않은 기존 ChatGPT 계정이 필요합니다. Platform API 키는 하나만 등록할 수 있으며, /v1/models와 상태 없는 HTTP /v1/responses 폴백에만 사용됩니다."}
        </p>
        {!isEdit && !prerequisiteSatisfied ? (
          <p className="text-xs text-destructive">
            먼저 ChatGPT 계정을 추가하거나 다시 활성화하세요. Platform 키는 단독으로 사용할 수 없습니다.
          </p>
        ) : null}
      </div>

      {error ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/10 px-2 py-1 text-xs text-destructive">
          {error}
        </p>
      ) : null}

      <DialogFooter>
        <Button type="submit" disabled={busy || !canSubmit}>
          {isEdit ? "변경 사항 저장" : "API 키 추가"}
        </Button>
      </DialogFooter>
    </form>
  );
}
