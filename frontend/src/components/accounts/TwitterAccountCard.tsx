import { motion } from "framer-motion";
import { MoreVertical, Trash2 } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { initialsFromName } from "@/lib/format";
import type { TwitterAccount } from "@/types/twitterAccount";

interface TwitterAccountCardProps {
  account: TwitterAccount;
  onDisconnect: () => void;
  isDisconnecting?: boolean;
}

export function TwitterAccountCard({ account, onDisconnect, isDisconnecting }: TwitterAccountCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <Card className="transition-colors hover:border-border-strong">
        <CardContent className="flex items-center justify-between gap-4 p-5">
          <div className="flex min-w-0 items-center gap-3">
            <Avatar className="h-11 w-11 border border-border">
              <AvatarImage src={account.profile_image_url ?? undefined} alt={account.display_name} />
              <AvatarFallback>{initialsFromName(account.display_name)}</AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">@{account.username}</p>
              <p className="truncate text-xs text-subtle-foreground">{account.display_name}</p>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                disabled={isDisconnecting}
                aria-label={`Ações da conta @${account.username}`}
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem variant="destructive" onSelect={onDisconnect}>
                <Trash2 className="h-4 w-4" />
                Desconectar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardContent>
      </Card>
    </motion.div>
  );
}
