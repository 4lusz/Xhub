import { AtSign } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { initialsFromName } from "@/lib/format";
import { useTwitterAccounts } from "@/hooks/useTwitterAccounts";

interface AccountSelectorProps {
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}

export function AccountSelector({ selectedIds, onChange }: AccountSelectorProps) {
  const { data: accounts, isLoading } = useTwitterAccounts();

  const toggle = (id: string) => {
    onChange(
      selectedIds.includes(id) ? selectedIds.filter((current) => current !== id) : [...selectedIds, id],
    );
  };

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {Array.from({ length: 2 }).map((_, index) => (
          <Skeleton key={index} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  if (!accounts || accounts.length === 0) {
    return (
      <EmptyState
        icon={<AtSign className="h-5 w-5" />}
        title="Nenhuma conta conectada"
        description="Conecte uma conta do X em “Contas do X” antes de criar um post."
      />
    );
  }

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {accounts.map((account) => {
        const isSelected = selectedIds.includes(account.id);
        return (
          <button
            key={account.id}
            type="button"
            onClick={() => toggle(account.id)}
            className={cn(
              "flex items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors",
              isSelected
                ? "border-primary bg-primary/10"
                : "border-border bg-surface hover:border-border-strong",
            )}
          >
            <Checkbox checked={isSelected} onCheckedChange={() => toggle(account.id)} />
            <Avatar className="h-8 w-8 border border-border">
              <AvatarImage src={account.profile_image_url ?? undefined} alt={account.display_name} />
              <AvatarFallback>{initialsFromName(account.display_name)}</AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">@{account.username}</p>
              <p className="truncate text-xs text-subtle-foreground">{account.display_name}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
