import { useEffect, useMemo, useState } from "react";

import { CopyButton } from "@/components/copy-button";
import { getRuntimeConnectAddress } from "@/features/accounts/api";

const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

function resolveConnectAddress(hostname: string, runtimeAddress: string | null): string {
  const normalizedRuntimeAddress = runtimeAddress?.trim() ?? "";
  if (normalizedRuntimeAddress) {
    return normalizedRuntimeAddress;
  }

  const normalized = hostname.trim().toLowerCase();
  if (!normalized || LOOPBACK_HOSTS.has(normalized)) {
    return "<codex-lb-ip-or-dns>";
  }
  return hostname;
}

export function WindowsOauthHelp() {
  const runtimeHost = typeof window !== "undefined" ? window.location.hostname : "";
  const [runtimeConnectAddress, setRuntimeConnectAddress] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void getRuntimeConnectAddress()
      .then((response) => {
        if (!active) return;
        const value = response.connectAddress?.trim();
        if (value) {
          setRuntimeConnectAddress(value);
        }
      })
      .catch(() => {
        // Keep hostname-based fallback if runtime connect address is unavailable.
      });

    return () => {
      active = false;
    };
  }, []);

  const connectAddress = useMemo(
    () => resolveConnectAddress(runtimeHost, runtimeConnectAddress),
    [runtimeHost, runtimeConnectAddress],
  );

  const commands = useMemo(
    () =>
      [
        "sc.exe config iphlpsvc start= auto",
        "sc.exe start iphlpsvc",
        "",
        "netsh interface portproxy delete v4tov4 listenaddress=127.0.0.1 listenport=1455",
        `netsh interface portproxy add v4tov4 listenaddress=127.0.0.1 listenport=1455 connectaddress=${connectAddress} connectport=1455`,
        "netsh interface portproxy show v4tov4",
      ].join("\n"),
    [connectAddress],
  );

  return (
    <div className="space-y-3 rounded-xl border bg-card p-4">
      <div>
        <h2 className="text-sm font-semibold">Windows OAuth 도움말</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Windows에서 브라우저 로그인이 실패하면, OAuth 콜백이
          <code className="mx-1 rounded bg-muted px-1 py-0.5">localhost:1455</code>
          에서 이 서버로 도달하도록 로컬 포트 포워딩을 만드세요.
        </p>
      </div>

      <p className="text-xs text-muted-foreground">
        런타임이 감지한 연결 주소:
        <code className="ml-1 rounded bg-muted px-1 py-0.5">{connectAddress}</code>
      </p>

      <pre className="overflow-x-auto rounded-lg border bg-muted/20 p-3 text-xs">
        <code>{commands}</code>
      </pre>

      <div className="flex flex-wrap items-center gap-2">
        <CopyButton value={commands} label="명령어 복사" />
        <span className="text-xs text-muted-foreground">PowerShell을 관리자 권한으로 실행하세요.</span>
      </div>
    </div>
  );
}
