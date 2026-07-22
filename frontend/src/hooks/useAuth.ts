import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import {
  changePassword as changePasswordRequest,
  login as loginRequest,
  logout as logoutRequest,
  removeSecurityQuestion as removeSecurityQuestionRequest,
  setSecurityQuestion as setSecurityQuestionRequest,
  verifySecurityAnswer as verifySecurityAnswerRequest,
} from "@/services/auth";
import { isSecondFactorRequired } from "@/types/auth";
import { useAuthStore } from "@/stores/authStore";
import { currentUserKey, useCurrentUser } from "@/hooks/useCurrentUser";
import { useToast } from "@/hooks/use-toast";

/**
 * Sessão combinada: presença do token (autenticação) + perfil real do
 * usuário via `GET /auth/me` (nome, e-mail, papel). `isAdmin` deriva
 * diretamente de `user.role`, sem sondas indiretas.
 */
export function useSession() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const isAuthenticated = Boolean(accessToken);
  const currentUser = useCurrentUser();

  return {
    isAuthenticated,
    user: currentUser.data ?? null,
    userId: currentUser.data?.id ?? null,
    isLoadingUser: isAuthenticated && currentUser.isLoading,
    isAdmin: currentUser.data?.role === "admin",
  };
}

export function useLogin() {
  const setTokens = useAuthStore((state) => state.setTokens);
  const navigate = useNavigate();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      loginRequest(email, password),
    onSuccess: (response) => {
      // Segundo fator (ver docs/AUDITORIA_SEGURANCA.md): a página de
      // login lê `login.data` para decidir se mostra o desafio da
      // pergunta -- aqui só navegamos/gravamos token no caso normal,
      // nunca no caso de segundo fator pendente.
      if (isSecondFactorRequired(response)) return;
      setTokens(response);
      navigate("/dashboard", { replace: true });
    },
    onError: (error: Error) => {
      toast({
        variant: "destructive",
        title: "Não foi possível entrar",
        description: error.message,
      });
    },
  });
}

/** Segunda etapa do login (pergunta de segurança) -- mesmo tratamento
 * de sucesso de um login normal em uma única etapa. */
export function useVerifySecurityAnswer() {
  const setTokens = useAuthStore((state) => state.setTokens);
  const navigate = useNavigate();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ pendingToken, answer }: { pendingToken: string; answer: string }) =>
      verifySecurityAnswerRequest(pendingToken, answer),
    onSuccess: (tokens) => {
      setTokens(tokens);
      navigate("/dashboard", { replace: true });
    },
    onError: (error: Error) => {
      toast({
        variant: "destructive",
        title: "Resposta incorreta",
        description: error.message,
      });
    },
  });
}

export function useSetSecurityQuestion() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ question, answer }: { question: string; answer: string }) =>
      setSecurityQuestionRequest(question, answer),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: currentUserKey });
      toast({ variant: "success", title: "Pergunta de segurança configurada" });
    },
    onError: (error: Error) => {
      toast({
        variant: "destructive",
        title: "Não foi possível configurar",
        description: error.message,
      });
    },
  });
}

export function useRemoveSecurityQuestion() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: removeSecurityQuestionRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: currentUserKey });
      toast({ variant: "success", title: "Pergunta de segurança removida" });
    },
    onError: (error: Error) => {
      toast({
        variant: "destructive",
        title: "Não foi possível remover",
        description: error.message,
      });
    },
  });
}

/**
 * Conclui o primeiro acesso obrigatório (ver
 * docs/ROADMAP_PRIMEIRO_ACESSO.md). Ao suceder: limpa a flag local
 * (`mustChangePassword`) -- o backend já confirmou a troca, então as
 * próximas chamadas (incluindo `GET /auth/me`, agora liberado) vão
 * funcionar normalmente -- e navega para a tela inicial.
 */
export function useChangePassword() {
  const setMustChangePassword = useAuthStore((state) => state.setMustChangePassword);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (newPassword: string) => changePasswordRequest(newPassword),
    onSuccess: () => {
      setMustChangePassword(false);
      queryClient.invalidateQueries({ queryKey: currentUserKey });
      toast({ variant: "success", title: "Senha atualizada com sucesso" });
      navigate("/dashboard", { replace: true });
    },
    onError: (error: Error) => {
      toast({
        variant: "destructive",
        title: "Não foi possível atualizar sua senha",
        description: error.message,
      });
    },
  });
}

export function useLogout() {
  const clearSession = useAuthStore((state) => state.clearSession);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      if (refreshToken) {
        await logoutRequest(refreshToken).catch(() => undefined);
      }
    },
    onSettled: () => {
      clearSession();
      queryClient.clear();
      navigate("/login", { replace: true });
    },
  });
}
