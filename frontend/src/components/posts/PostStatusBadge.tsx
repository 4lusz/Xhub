import { CalendarClock, CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { PostStatus } from "@/types/post";

const STATUS_CONFIG: Record<
  PostStatus,
  { label: string; variant: "default" | "secondary" | "success" | "warning" | "destructive"; icon: React.ComponentType<{ className?: string }> }
> = {
  draft: { label: "Rascunho", variant: "secondary", icon: CircleDashed },
  pending: { label: "Pendente", variant: "secondary", icon: CircleDashed },
  scheduled: { label: "Agendado", variant: "warning", icon: CalendarClock },
  publishing: { label: "Publicando", variant: "default", icon: Loader2 },
  published: { label: "Publicado", variant: "success", icon: CheckCircle2 },
  failed: { label: "Falhou", variant: "destructive", icon: XCircle },
};

export function PostStatusBadge({ status }: { status: PostStatus }) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  return (
    <Badge variant={config.variant}>
      <Icon className={cn("h-3 w-3", status === "publishing" && "animate-spin")} />
      {config.label}
    </Badge>
  );
}
