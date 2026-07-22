import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Loader2, LogIn, ShieldQuestion } from "lucide-react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLogin, useVerifySecurityAnswer } from "@/hooks/useAuth";
import { isSecondFactorRequired } from "@/types/auth";

const loginSchema = z.object({
  email: z.string().min(1, "Informe seu e-mail.").email("E-mail inválido."),
  password: z.string().min(1, "Informe sua senha."),
});

type LoginFormValues = z.infer<typeof loginSchema>;

const answerSchema = z.object({
  answer: z.string().min(1, "Informe a resposta."),
});

type AnswerFormValues = z.infer<typeof answerSchema>;

/**
 * Segunda etapa do login (ver docs/AUDITORIA_SEGURANCA.md) -- só
 * aparece para quem configurou uma pergunta de segurança (hoje,
 * administradores). `pendingToken` nunca é um token de acesso válido
 * em nenhuma outra rota, só serve para completar esta etapa.
 */
function SecurityQuestionChallenge({
  pendingToken,
  question,
}: {
  pendingToken: string;
  question: string;
}) {
  const verifyAnswer = useVerifySecurityAnswer();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AnswerFormValues>({
    resolver: zodResolver(answerSchema),
  });

  const onSubmit = (values: AnswerFormValues) => {
    verifyAnswer.mutate({ pendingToken, answer: values.answer });
  };

  return (
    <Card className="border-border bg-surface/80 backdrop-blur-sm">
      <CardHeader className="space-y-1 text-center">
        <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-primary/15 text-primary">
          <ShieldQuestion className="h-5 w-5" />
        </div>
        <CardTitle className="text-xl">Confirme sua identidade</CardTitle>
        <CardDescription>Responda à pergunta de segurança para concluir o login.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="answer">{question}</Label>
            <Input
              id="answer"
              type="text"
              autoComplete="off"
              autoFocus
              {...register("answer")}
            />
            {errors.answer && <p className="text-xs text-destructive">{errors.answer.message}</p>}
          </div>

          <Button type="submit" className="mt-2 w-full" disabled={verifyAnswer.isPending}>
            {verifyAnswer.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ShieldQuestion className="h-4 w-4" />
            )}
            Confirmar
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export function LoginPage() {
  const login = useLogin();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = (values: LoginFormValues) => {
    login.mutate(values);
  };

  if (login.data && isSecondFactorRequired(login.data)) {
    return (
      <SecurityQuestionChallenge
        pendingToken={login.data.pending_token}
        question={login.data.question}
      />
    );
  }

  return (
    <Card className="border-border bg-surface/80 backdrop-blur-sm">
      <CardHeader className="space-y-1 text-center">
        <CardTitle className="text-xl">Entrar no XHub</CardTitle>
        <CardDescription>
          Acesso restrito a contas criadas por um administrador.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="email">E-mail</Label>
            <Input
              id="email"
              type="email"
              autoComplete="username"
              placeholder="voce@empresa.com"
              {...register("email")}
            />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Senha</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              {...register("password")}
            />
            {errors.password && (
              <p className="text-xs text-destructive">{errors.password.message}</p>
            )}
          </div>

          <Button type="submit" className="mt-2 w-full" disabled={login.isPending}>
            {login.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <LogIn className="h-4 w-4" />
            )}
            Entrar
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
