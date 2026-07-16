import { useState } from "react";
import { CalendarClock, Loader2, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DateTimePicker } from "@/components/common/DateTimePicker";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

interface PublishOrScheduleDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onPublishNow: () => void;
  onSchedule: (isoDateTime: string) => void;
  isPublishing?: boolean;
  isScheduling?: boolean;
}

function minDateTimeLocal(): string {
  const now = new Date(Date.now() + 5 * 60 * 1000);
  const offset = now.getTimezoneOffset();
  const local = new Date(now.getTime() - offset * 60 * 1000);
  return local.toISOString().slice(0, 16);
}

export function PublishOrScheduleDialog({
  isOpen,
  onClose,
  onPublishNow,
  onSchedule,
  isPublishing,
  isScheduling,
}: PublishOrScheduleDialogProps) {
  const [scheduledFor, setScheduledFor] = useState("");
  const isBusy = isPublishing || isScheduling;

  const handleSchedule = () => {
    if (!scheduledFor) return;
    // O <input datetime-local> não inclui timezone; interpretamos como
    // horário local do navegador e convertemos para ISO com offset.
    const localDate = new Date(scheduledFor);
    onSchedule(localDate.toISOString());
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !isBusy && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Texto pronto — como publicar?</DialogTitle>
          <DialogDescription>
            O post já foi salvo com o texto revisado. Escolha publicar agora em todas as contas
            selecionadas ou agendar para mais tarde.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <Button
            className="w-full justify-start"
            size="lg"
            onClick={onPublishNow}
            disabled={isBusy}
          >
            {isPublishing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Publicar agora
          </Button>

          <div className="flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs font-medium uppercase tracking-wide text-subtle-foreground">
              ou
            </span>
            <Separator className="flex-1" />
          </div>

          <div className="space-y-2 rounded-lg border border-border p-4">
            <Label className="flex items-center gap-2 text-sm">
              <CalendarClock className="h-4 w-4 text-muted-foreground" />
              Agendar para mais tarde
            </Label>
            <DateTimePicker
              value={scheduledFor}
              onChange={setScheduledFor}
              min={minDateTimeLocal()}
              disabled={isBusy}
            />
            <Button
              variant="secondary"
              className="w-full"
              onClick={handleSchedule}
              disabled={!scheduledFor || isBusy}
            >
              {isScheduling ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarClock className="h-4 w-4" />}
              Agendar publicação
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={isBusy}>
            Deixar como rascunho por agora
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
