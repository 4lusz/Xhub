/**
 * Formato de erro retornado pela API do XHub.
 *
 * Toda exceção de negócio no backend (`BaseAppException` e
 * subclasses) é convertida, na camada de rota, em uma resposta HTTP
 * com corpo `{ "detail": "<mensagem>" }` (padrão do FastAPI
 * `HTTPException`) -- `detail` como string, já pensada para ser
 * exibida ao usuário.
 *
 * Exceção: um 422 de validação do PRÓPRIO Pydantic (campo obrigatório
 * ausente, fora do intervalo, etc.) nunca passa pela rota -- o FastAPI
 * responde antes disso, com `detail` como uma LISTA de
 * `{loc, msg, type}` (formato padrão do FastAPI/Pydantic, não
 * controlado por este projeto). `services/api.ts` trata os dois
 * formatos ao montar `ApiError.message`.
 */
export interface ApiValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiErrorBody {
  detail: string | ApiValidationErrorItem[];
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}
