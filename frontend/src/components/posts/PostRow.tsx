import { motion } from "framer-motion";
import { MoreVertical, Send, Trash2, XCircle } from "lucide-react";

import { PostAccountsBreakdown } from "@/components/posts/PostAccountsBreakdown";
import { PostStatusBadge } from "@/components/posts/PostStatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDateTime, formatRelativeTime } from "@/lib/format";
import type { Post } from "@/types/post";

interface PostRowProps {
  post: Post;
  onPublish?: () => void;
  onDelete?: () => void;
  onCancelSchedule?: () => void;
  isBusy?: boolean;
}

export function PostRow({ post, onPublish, onDelete, onCancelSchedule, isBusy }: PostRowProps) {
  const hasActions = Boolean(onPublish || onDelete || onCancelSchedule);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.2 }}>
      <Card>
        <CardContent className="flex items-start justify-between gap-4 p-5">
          <div className="min-w-0 space-y-1.5">
            <p className="whitespace-pre-wrap text-sm text-foreground">{post.text}</p>
            <div className="flex flex-wrap items-center gap-2 text-xs text-subtle-foreground">
              <span title={formatDateTime(post.created_at)}>
                {formatRelativeTime(post.created_at)}
              </span>
              <span>·</span>
              <PostStatusBadge status={post.status} />
            </div>
            <PostAccountsBreakdown accounts={post.accounts} />
          </div>

          {hasActions && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" disabled={isBusy} aria-label="Ações do post">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {onPublish && (
                  <DropdownMenuItem onSelect={onPublish}>
                    <Send className="h-4 w-4" />
                    Publicar agora
                  </DropdownMenuItem>
                )}
                {onCancelSchedule && (
                  <DropdownMenuItem variant="destructive" onSelect={onCancelSchedule}>
                    <XCircle className="h-4 w-4" />
                    Cancelar agendamento
                  </DropdownMenuItem>
                )}
                {onDelete && (
                  <DropdownMenuItem variant="destructive" onSelect={onDelete}>
                    <Trash2 className="h-4 w-4" />
                    Excluir
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
