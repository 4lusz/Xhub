import { cn } from "@/lib/utils";

const MAX_LENGTH = 280;
const WARNING_THRESHOLD = 260;

interface CharacterCounterProps {
  length: number;
  max?: number;
  className?: string;
}

export function CharacterCounter({ length, max = MAX_LENGTH, className }: CharacterCounterProps) {
  const remaining = max - length;
  const isOverLimit = remaining < 0;
  const isNearLimit = length >= WARNING_THRESHOLD && !isOverLimit;

  return (
    <span
      className={cn(
        "font-mono-xhub text-xs tabular-nums",
        isOverLimit
          ? "font-medium text-destructive"
          : isNearLimit
            ? "text-warning"
            : "text-subtle-foreground",
        className,
      )}
    >
      {remaining}
    </span>
  );
}
