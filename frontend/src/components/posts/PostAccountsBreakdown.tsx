import { AlertCircle, CheckCircle2, Clock } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { PostAccount } from "@/types/post";

const STATUS_CONFIG: Record<
  PostAccount["status"],
  { icon: React.ComponentType<{ className?: string }>; className: string }
> = {
  published: { icon: CheckCircle2, className: "text-success" },
  failed: { icon: AlertCircle, className: "text-destructive" },
  pending: { icon: Clock, className: "text-muted-foreground" },
};

/**
 * Detalhamento por conta de um post (`Post.accounts`, exposto pelo
 * backend em `GET /posts` e `GET /posts/{id}`). Só faz sentido mostrar
 * quando há mais de uma conta — com uma única conta, o status agregado
 * do post já conta a história inteira.
 */
export function PostAccountsBreakdown({ accounts }: { accounts: PostAccount[] }) {
  if (accounts.length <= 1) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {accounts.map((account) => {
        const config = STATUS_CONFIG[account.status];
        const Icon = config.icon;

        return (
          <Tooltip key={account.twitter_account_id}>
            <TooltipTrigger asChild>
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full border border-border bg-surface px-2 py-0.5 text-xs",
                  config.className,
                )}
              >
                <Icon className="h-3 w-3" />@{account.username}
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="font-medium">@{account.username}</p>
              <p className="capitalize">{account.status}</p>
            </TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}
