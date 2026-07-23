import { motion } from "framer-motion";
import { AlertTriangle, Sparkles } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Textarea } from "@/components/ui/textarea";
import { CharacterCounter } from "@/components/common/CharacterCounter";
import { cn } from "@/lib/utils";
import { initialsFromName } from "@/lib/format";
import type { AccountPreview } from "@/types/intelligentPublication";

interface VariationAccountCardProps {
  account: AccountPreview;
  value: string;
  isEmpty: boolean;
  /** Bloqueia a confirmação (hoje só no caso de 5+ contas, variação obrigatória). */
  isDuplicate: boolean;
  /** Mesmo texto de outra conta, mas SEM bloquear (2-4 contas, variação opcional) -- apenas um alerta visual, o usuário pode confirmar mesmo assim. */
  isDuplicateWarning?: boolean;
  onChange: (value: string) => void;
}

export function VariationAccountCard({
  account,
  value,
  isEmpty,
  isDuplicate,
  isDuplicateWarning,
  onChange,
}: VariationAccountCardProps) {
  const isOverLimit = value.length > 280;
  const hasIssue = isEmpty || isDuplicate || isOverLimit;
  const hasWarning = !hasIssue && isDuplicateWarning;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        "space-y-2 rounded-lg border bg-surface p-3 transition-colors",
        hasIssue ? "border-destructive/50" : hasWarning ? "border-warning/50" : "border-border",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Avatar className="h-6 w-6 border border-border">
            <AvatarFallback className="text-[10px]">
              {initialsFromName(account.display_name)}
            </AvatarFallback>
          </Avatar>
          <span className="truncate text-xs font-medium text-foreground">
            {account.display_name}
          </span>
          <span className="shrink-0 text-xs text-subtle-foreground">@{account.username}</span>
        </div>
        <CharacterCounter length={value.length} />
      </div>

      <Textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={3}
        className={cn(
          "resize-none text-sm",
          hasIssue && "border-destructive/60 focus-visible:ring-destructive/40",
        )}
      />

      <div className="flex min-h-[18px] items-center justify-between">
        {account.is_variation ? (
          <span className="inline-flex items-center gap-1 text-xs text-primary">
            <Sparkles className="h-3 w-3" />
            Variação gerada por IA
          </span>
        ) : (
          <span className="text-xs text-subtle-foreground">Texto original</span>
        )}

        {(isEmpty || isDuplicate) && (
          <span className="inline-flex items-center gap-1 text-xs text-destructive">
            <AlertTriangle className="h-3 w-3" />
            {isEmpty ? "Texto vazio" : "Texto duplicado"}
          </span>
        )}
        {hasWarning && (
          <span className="inline-flex items-center gap-1 text-xs text-warning">
            <AlertTriangle className="h-3 w-3" />
            Igual a outra conta
          </span>
        )}
      </div>
    </motion.div>
  );
}
