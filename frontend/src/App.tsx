import { useHealthCheck, useDbHealthCheck } from "@/hooks/useHealthCheck";
import { StatusCard } from "@/components/StatusCard";

function App() {
  const api = useHealthCheck();
  const db = useDbHealthCheck();

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">XHub</h1>
          <p className="text-sm text-neutral-500">
            Etapa 1 &mdash; ambiente de desenvolvimento
          </p>
        </div>

        <div className="space-y-3">
          <StatusCard
            label="API (FastAPI)"
            isLoading={api.isLoading}
            isError={api.isError}
            okText="online"
          />
          <StatusCard
            label="Banco de dados (PostgreSQL)"
            isLoading={db.isLoading}
            isError={db.isError}
            okText="conectado"
          />
        </div>

        <p className="text-center text-xs text-neutral-600">
          Quando os dois status acima ficarem verdes, o ambiente esta
          pronto para a proxima etapa.
        </p>
      </div>
    </div>
  );
}

export default App;
