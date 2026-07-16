import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  blockUser,
  changeUserRole,
  createUser,
  listUsers,
  resetUserPassword,
  unblockUser,
} from "@/services/users";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/types/api";
import type { CreateUserPayload, UserRole } from "@/types/user";

export const usersKey = ["admin", "users"] as const;

export function useUsers() {
  return useQuery({
    queryKey: usersKey,
    queryFn: () => listUsers({ limit: 200 }),
  });
}

function useInvalidateUsers() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: usersKey });
}

export function useCreateUser() {
  const invalidate = useInvalidateUsers();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (payload: CreateUserPayload) => createUser(payload),
    onSuccess: (user) => {
      invalidate();
      toast({ variant: "success", title: "Usuário criado", description: user.email });
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Não foi possível criar o usuário", description: error.message });
    },
  });
}

export function useToggleUserBlock() {
  const invalidate = useInvalidateUsers();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ userId, block }: { userId: string; block: boolean }) =>
      block ? blockUser(userId) : unblockUser(userId),
    onSuccess: (user) => {
      invalidate();
      toast({ title: user.is_blocked ? "Usuário bloqueado" : "Usuário desbloqueado" });
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Não foi possível atualizar o usuário", description: error.message });
    },
  });
}

/**
 * Redefinição administrativa de senha (ver
 * docs/ROADMAP_PRIMEIRO_ACESSO.md). O resultado (que inclui a senha
 * temporária em texto puro, exibida uma única vez) é tratado pelo
 * componente chamador -- não colocamos a senha em um toast, que soma
 * mais exposição/persistência desnecessária a um dado sensível.
 */
export function useResetUserPassword() {
  const invalidate = useInvalidateUsers();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (userId: string) => resetUserPassword(userId),
    onSuccess: () => {
      invalidate();
    },
    onError: (error: ApiError) => {
      toast({
        variant: "destructive",
        title: "Não foi possível redefinir a senha",
        description: error.message,
      });
    },
  });
}

export function useChangeUserRole() {
  const invalidate = useInvalidateUsers();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: UserRole }) => changeUserRole(userId, role),
    onSuccess: () => {
      invalidate();
      toast({ title: "Papel atualizado" });
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Não foi possível atualizar o papel", description: error.message });
    },
  });
}
