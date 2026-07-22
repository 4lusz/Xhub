/**
 * Helpers de formatação reutilizados por várias telas. Mantidos aqui
 * para não duplicar lógica de formatação de data/texto em cada
 * componente.
 */

const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

const relativeFormatter = new Intl.RelativeTimeFormat("pt-BR", {
  numeric: "auto",
});

const compactNumberFormatter = new Intl.NumberFormat("pt-BR", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatDateTime(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return dateTimeFormatter.format(date);
}

export function formatDate(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return dateFormatter.format(date);
}

export function formatRelativeTime(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  const diffMs = date.getTime() - Date.now();
  const diffSeconds = Math.round(diffMs / 1000);
  const absSeconds = Math.abs(diffSeconds);

  if (absSeconds < 60) return relativeFormatter.format(diffSeconds, "second");
  const diffMinutes = Math.round(diffSeconds / 60);
  if (Math.abs(diffMinutes) < 60) return relativeFormatter.format(diffMinutes, "minute");
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) return relativeFormatter.format(diffHours, "hour");
  const diffDays = Math.round(diffHours / 24);
  if (Math.abs(diffDays) < 30) return relativeFormatter.format(diffDays, "day");
  const diffMonths = Math.round(diffDays / 30);
  if (Math.abs(diffMonths) < 12) return relativeFormatter.format(diffMonths, "month");
  const diffYears = Math.round(diffMonths / 12);
  return relativeFormatter.format(diffYears, "year");
}

export function initialsFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0]}${parts[parts.length - 1]![0]}`.toUpperCase();
}

export function pluralize(count: number, singular: string, plural: string): string {
  return count === 1 ? singular : plural;
}

export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1).trimEnd()}…`;
}

/** Numero grande e legivel (ex.: 12400 -> "12,4 mil"). `null`/`undefined`
 * vira "—" -- usado nas telas de Resultados para metricas que podem nao
 * ter sido coletadas ainda. */
export function formatCompactNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return compactNumberFormatter.format(value);
}

/** Variacao percentual com sinal (ex.: 0.256 -> "+26%", -0.5 -> "-50%").
 * `null` (sem dado do periodo anterior para comparar) vira "—". */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const rounded = Math.round(value * 100);
  return `${rounded > 0 ? "+" : ""}${rounded}%`;
}
