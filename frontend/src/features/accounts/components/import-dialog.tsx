import { useState } from "react";
import type { FormEvent } from "react";

import { Button } from "@/components/ui/button";
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

export type ImportDialogProps = {
  open: boolean;
  busy: boolean;
  error: string | null;
  onOpenChange: (open: boolean) => void;
  onImport: (file: File) => Promise<void>;
};

export function ImportDialog({
  open,
  busy,
  error,
  onOpenChange,
  onImport,
}: ImportDialogProps) {
  const [file, setFile] = useState<File | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      return;
    }
    await onImport(file);
    onOpenChange(false);
    setFile(null);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>auth.json 가져오기</DialogTitle>
          <DialogDescription>내보낸 계정 auth.json 파일을 업로드하세요.</DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="auth-json-file">파일</Label>
            <Input
              id="auth-json-file"
              type="file"
              accept="application/json,.json"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </div>

          {error ? (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 px-2 py-1 text-xs text-destructive">
              {error}
            </p>
          ) : null}

          <DialogFooter>
            <Button type="submit" disabled={busy || !file}>
              가져오기
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
