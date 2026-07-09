import axios from "axios";

/**
 * Instancia Axios central. Nas proximas etapas (autenticacao) sera
 * adicionado um interceptor para anexar o JWT e tratar refresh token.
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});
