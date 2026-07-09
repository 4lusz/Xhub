interface StatusCardProps {
  label: string;
  isLoading: boolean;
  isError: boolean;
  okText: string;
}

export function StatusCard({ label, isLoading, isError, okText }: StatusCardProps) {
  const dotColor = isLoading ? "bg-yellow-500" : isError ? "bg-red-500" : "bg-emerald-500";
  const text = isLoading ? "verificando..." : isError ? "falha na conexao" : okText;

  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3">
      <span className="text-sm text-neutral-300">{label}</span>
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${dotColor}`} />
        <span className="text-sm text-neutral-400">{text}</span>
      </div>
    </div>
  );
}
