import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Loader2, ShieldCheck } from "lucide-react";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/common/Logo";
import { useChangePassword } from "@/hooks/useAuth";

const firstAccessSchema = z
  .object({
    newPassword: z.string().min(8, "A senha deve ter pelo menos 8 caracteres."),
    confirmPassword: z.string().min(1, "Confirme a nova senha."),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "As senhas não coincidem.",
    path: ["confirmPassword"],
  });

type FirstAccessFormValues = z.infer<typeof firstAccessSchema>;

/**
 * Tela obrigatória de primeiro acesso (ver
 * docs/ROADMAP_PRIMEIRO_ACESSO.md) -- deliberadamente distinta da
 * tela de login (`pages/LoginPage.tsx`, dentro de `AuthLayout`):
 * enquadramento de segurança explícito (ícone, título e explicação
 * sobre por que a troca é obrigatória), em vez de um formulário de
 * "entrar". `ProtectedRoute` garante que nenhuma outra tela do
 * sistema é alcançável enquanto esta não for concluída.
 */
export function FirstAccessPage() {
  const changePassword = useChangePassword();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FirstAccessFormValues>({
    resolver: zodResolver(firstAccessSchema),
  });

  const onSubmit = (values: FirstAccessFormValues) => {
    changePassword.mutate(values.newPassword);
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">
      <div className="pointer-events-none absolute inset-0 bg-grid-fade" />
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[560px] w-[560px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-warning/10 blur-[120px]"
        aria-hidden="true"
      />

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Logo iconClassName="h-8 w-8" className="text-xl" />
        </div>

        <Card className="border-border bg-surface/80 backdrop-blur-sm">
          <CardHeader className="items-center space-y-3 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-warning/15 text-warning">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div className="space-y-1.5">
              <h1 className="text-xl font-semibold text-foreground">Defina sua senha de acesso</h1>
              <p className="text-sm text-muted-foreground">
                Por motivos de segurança, você está usando uma senha temporária. Antes de continuar,
                crie uma senha definitiva conhecida apenas por você.
              </p>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert variant="warning">
              <AlertDescription>
                Esta etapa é obrigatória e só precisa ser feita uma vez. Depois de definida, a senha
                temporária deixa de funcionar.
              </AlertDescription>
            </Alert>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div className="space-y-2">
                <Label htmlFor="newPassword">Nova senha</Label>
                <Input
                  id="newPassword"
                  type="password"
                  autoComplete="new-password"
                  placeholder="••••••••"
                  {...register("newPassword")}
                />
                {errors.newPassword && (
                  <p className="text-xs text-destructive">{errors.newPassword.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirmar nova senha</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  placeholder="••••••••"
                  {...register("confirmPassword")}
                />
                {errors.confirmPassword && (
                  <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
                )}
              </div>

              <Button type="submit" className="mt-2 w-full" disabled={changePassword.isPending}>
                {changePassword.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ShieldCheck className="h-4 w-4" />
                )}
                Confirmar nova senha
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
