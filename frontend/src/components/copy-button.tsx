import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";

export type CopyButtonProps = {
  value: string;
  label?: string;
  iconOnly?: boolean;
};

export function CopyButton({ value, label = "복사", iconOnly = false }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      toast.success("클립보드에 복사했습니다");
      setTimeout(() => setCopied(false), 1200);
    } catch {
      toast.error("복사하지 못했습니다");
    }
  };

  return (
    <Button
      type="button"
      variant="outline"
      size={iconOnly ? "icon-sm" : "sm"}
      onClick={handleCopy}
      aria-label={copied ? `${label} 완료` : label}
      title={copied ? "복사됨" : label}
    >
      {copied ? <Check className={iconOnly ? "h-4 w-4" : "mr-2 h-4 w-4"} /> : <Copy className={iconOnly ? "h-4 w-4" : "mr-2 h-4 w-4"} />}
      {iconOnly ? null : copied ? "복사됨" : label}
    </Button>
  );
}
