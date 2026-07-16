import { useState } from "react";
import { AlertTriangle, Check, Copy } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ResetPasswordResult } from "@/types/user";

interface ResetPasswordResultDialogProps {
  result: ResetPasswordResult | null;
  onClose: () => void;
}

/**
 * Exibe a senha temporária gerada por `POST
 * /admin/users/{id}/reset-password` (ver
 * docs/ROADMAP_PRIMEIRO_ACESSO.md) -- uma única vez, nunca recuperável
 * depois de fechado. O administrador nunca vê a senha ATUAL do
 * usuário, apenas esta nova senha temporária que ele mesmo acabou de
 * gerar.
 */
export function ResetPasswordResultDialog({ result, onClose }: ResetPasswordResultDialogProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.temporary_password);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog
      open={result !== null}
      onOpenChange={(open) => {
        if (!open) {
          setCopied(false);
          onClose();
        }
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Senha temporária gerada</DialogTitle>
          <DialogDescription>
            Comunique esta senha para <strong>{result?.user.name}</strong> ({result?.user.email}).
            Ela só será exibida agora.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-3">
          <code className="flex-1 select-all font-mono text-sm text-foreground">
            {result?.temporary_password}
          </code>
          <Button type="button" variant="outline" size="sm" onClick={handleCopy}>
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copiado" : "Copiar"}
          </Button>
        </div>

        <Alert variant="warning">
          <AlertTriangle />
          <AlertDescription>
            No próximo login, o usuário será obrigado a definir uma nova senha antes de acessar o
            sistema. Esta senha temporária deixará de funcionar assim que ele concluir a troca.
          </AlertDescription>
        </Alert>

        <DialogFooter>
          <Button onClick={onClose}>Concluído</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
