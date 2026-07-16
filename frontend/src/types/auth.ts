export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  /** Primeiro acesso obrigatório: `true` enquanto a conta ainda usa uma senha temporária. */
  must_change_password: boolean;
}

export interface JwtPayload {
  sub: string;
  exp: number;
}
