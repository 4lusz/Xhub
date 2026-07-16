import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon: ReactNode;
  hint?: string;
  accent?: boolean;
}

export function StatCard({ label, value, icon, hint, accent }: StatCardProps) {
  return (
    <Card className="transition-colors hover:border-border-strong">
      <CardContent className="flex items-start justify-between p-6">
        <div className="space-y-1.5">
          <p className="text-sm text-muted-foreground">{label}</p>
          <div className="font-display text-3xl font-semibold tracking-tight text-foreground">
            {value}
          </div>
          {hint && <p className="text-xs text-subtle-foreground">{hint}</p>}
        </div>
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg",
            accent ? "bg-primary/15 text-primary" : "bg-surface-elevated text-muted-foreground",
          )}
        >
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}
