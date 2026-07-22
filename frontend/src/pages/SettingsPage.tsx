import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Loader2, LogOut, ShieldCheck, ShieldQuestion, Trash2 } from "lucide-react";
import { z } from "zod";

import { PageHeader } from "@/components/common/PageHeader";
import { SubscriptionCard } from "@/components/dashboard/SubscriptionCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useLogout,
  useRemoveSecurityQuestion,
  useSession,
  useSetSecurityQuestion,
} from "@/hooks/useAuth";
import { useCurrentUser } from "@/hooks/useCurrentUser";

const securityQuestionSchema = z.object({
  question: z.string().min(1, "Informe a pergunta.").max(200, "Pergunta muito longa."),
  answer: z.string().min(1, "Informe a resposta.").max(200, "Resposta muito longa."),
});

type SecurityQuestionFormValues = z.infer<typeof securityQuestionSchema>;

/**
 * Segundo fator simples de login (ver docs/AUDITORIA_SEGURANCA.md) --
 * hoje restrito a administradores. Opcional: sem pergunta configurada,
 * o login continua em uma única etapa (email+senha).
 */
function SecurityQuestionCard() {
  const { data: currentUser } = useCurrentUser();
  const setSecurityQuestion = useSetSecurityQuestion();
  const removeSecurityQuestion = useRemoveSecurityQuestion();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SecurityQuestionFormValues>({
    resolver: zodResolver(securityQuestionSchema),
  });

  const hasQuestion = Boolean(currentUser?.security_question);

  const onSubmit = (values: SecurityQuestionFormValues) => {
    setSecurityQuestion.mutate(
      { question: values.question, answer: values.answer },
      { onSuccess: () => reset() },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Segundo fator de login (pergunta de segurança)</CardTitle>
        <CardDescription>
          Uma camada extra de proteção para sua conta de administrador: além de e-mail e senha, o
          login pede a resposta de uma pergunta que só você conhece. Recomendamos usar uma
          resposta inventada, sem relação com fatos reais (ex.: uma palavra-código qualquer), em
          vez de uma resposta biográfica que alguém possa descobrir.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {hasQuestion && (
          <div className="flex items-center justify-between rounded-lg border border-success/30 bg-success/10 px-4 py-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-success" />
              <div>
                <p className="text-sm font-medium text-foreground">Configurada</p>
                <p className="text-xs text-muted-foreground">
                  Pergunta atual: {currentUser?.security_question}
                </p>
              </div>
            </div>
            <Badge variant="success">Ativa</Badge>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="question">
              {hasQuestion ? "Nova pergunta (substitui a atual)" : "Pergunta"}
            </Label>
            <Input
              id="question"
              placeholder="Ex.: Qual é a palavra-código desta conta?"
              {...register("question")}
            />
            {errors.question && (
              <p className="text-xs text-destructive">{errors.question.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="answer">Resposta</Label>
            <Input id="answer" type="password" autoComplete="off" {...register("answer")} />
            {errors.answer && <p className="text-xs text-destructive">{errors.answer.message}</p>}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={setSecurityQuestion.isPending}>
              {setSecurityQuestion.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ShieldQuestion className="h-4 w-4" />
              )}
              {hasQuestion ? "Substituir" : "Configurar"}
            </Button>
            {hasQuestion && (
              <Button
                type="button"
                variant="outline"
                onClick={() => removeSecurityQuestion.mutate()}
                disabled={removeSecurityQuestion.isPending}
              >
                <Trash2 className="h-4 w-4" />
                Remover
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

export function SettingsPage() {
  const logout = useLogout();
  const { isAdmin } = useSession();

  return (
    <div className="max-w-2xl space-y-8">
      <PageHeader title="Configurações" description="Preferências e sessão da sua conta no XHub." />

      <SubscriptionCard />

      {isAdmin && <SecurityQuestionCard />}

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
