import { LogOut } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { SubscriptionCard } from "@/components/dashboard/SubscriptionCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useLogout } from "@/hooks/useAuth";

export function SettingsPage() {
  const logout = useLogout();

  return (
    <div className="max-w-2xl space-y-8">
      <PageHeader title="Configurações" description="Preferências e sessão da sua conta no XHub." />

      <SubscriptionCard />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sessão</CardTitle>
          <CardDescription>
            Encerre sua sessão neste dispositivo. Seu token de acesso expira automaticamente por
            segurança.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={() => logout.mutate()} disabled={logout.isPending}>
            <LogOut className="h-4 w-4" />
            Sair da conta
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
