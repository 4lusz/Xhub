import { Info, Shield, UserCircle } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useSession } from "@/hooks/useAuth";

export function ProfilePage() {
  const { user, isAdmin, isLoadingUser } = useSession();

  return (
    <div className="max-w-2xl space-y-8">
      <PageHeader title="Perfil" description="Seus dados de identificação no XHub." />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <UserCircle className="h-4 w-4" />
            Dados da conta
          </CardTitle>
          <CardDescription>
            O XHub não possui autocadastro — sua conta foi criada por um administrador.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingUser ? (
            <div className="space-y-4">
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-5 w-full" />
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Nome</span>
                <span className="font-medium text-foreground">{user?.name ?? "—"}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">E-mail</span>
                <span className="font-medium text-foreground">{user?.email ?? "—"}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">ID do usuário</span>
                <span className="font-mono-xhub text-xs text-foreground">{user?.id ?? "—"}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Papel</span>
                {isAdmin ? (
                  <Badge>
                    <Shield className="h-3 w-3" />
                    Administrador
                  </Badge>
                ) : (
                  <Badge variant="secondary">Cliente</Badge>
                )}
              </div>
            </>
          )}

          <div className="flex items-start gap-2 rounded-md border border-border bg-surface px-3 py-2.5 text-xs text-muted-foreground">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              A edição de nome, e-mail e senha ainda não está disponível. Para alterar esses dados,
              fale com um administrador.
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
