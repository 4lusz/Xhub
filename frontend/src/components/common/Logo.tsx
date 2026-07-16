import { cn } from "@/lib/utils";

interface LogoMarkProps {
  className?: string;
}

/**
 * Marca do XHub: um nó se ramificando em três -- o motivo visual da
 * Publicação Inteligente (um texto original que se torna várias
 * variações), reaproveitado como identidade da marca.
 */
export function LogoMark({ className }: LogoMarkProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={cn("h-6 w-6", className)}
      aria-hidden="true"
    >
      <path
        d="M8 16 L15 16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.5"
      />
      <path
        d="M16 16 L23 8 M16 16 L25 16 M16 16 L23 24"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="7" cy="16" r="3.5" fill="currentColor" />
      <circle cx="24" cy="8" r="2.5" fill="currentColor" opacity="0.9" />
      <circle cx="26" cy="16" r="2.5" fill="currentColor" />
      <circle cx="24" cy="24" r="2.5" fill="currentColor" opacity="0.9" />
    </svg>
  );
}

interface LogoProps {
  className?: string;
  iconClassName?: string;
}

export function Logo({ className, iconClassName }: LogoProps) {
  return (
    <div className={cn("flex items-center gap-2 text-foreground", className)}>
      <LogoMark className={cn("text-primary", iconClassName)} />
      <span className="font-display text-base font-semibold tracking-tight">XHub</span>
    </div>
  );
}
