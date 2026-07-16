import * as React from "react";
import { CalendarClock } from "lucide-react";

import { cn } from "@/lib/utils";

export interface DateTimePickerProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> {
  value: string;
  onChange: (value: string) => void;
}

/**
 * Usa `<input type="datetime-local">` nativo em vez de uma biblioteca
 * de calendário dedicada -- suficiente para o único uso desta tela
 * (agendar publicação) e evita adicionar uma dependência extra não
 * solicitada. O valor trafega em horário local do navegador; a
 * conversão para ISO/UTC acontece no ponto de envio (ver
 * `pages/NewPostPage.tsx`).
 */
export const DateTimePicker = React.forwardRef<HTMLInputElement, DateTimePickerProps>(
  ({ value, onChange, className, ...props }, ref) => {
    return (
      <div className="relative">
        <CalendarClock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle-foreground" />
        <input
          ref={ref}
          type="datetime-local"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={cn(
            "flex h-10 w-full rounded-md border border-input bg-surface pl-9 pr-3 py-2 text-sm text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary",
            "[color-scheme:dark]",
            className,
          )}
          {...props}
        />
      </div>
    );
  },
);
DateTimePicker.displayName = "DateTimePicker";
