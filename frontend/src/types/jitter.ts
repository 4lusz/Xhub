/**
 * Configuracao do Jitter (ver docs/ROADMAP_JITTER.md) -- atraso
 * aleatorio aplicado entre publicacoes em contas diferentes de um
 * mesmo post, para reduzir padroes automatizados. Espelha
 * `JitterSettingsResponse`/`UpdateJitterSettingsRequest` do backend
 * (`app/routes/admin.py`).
 */
export interface JitterSettings {
  min_seconds: number;
  max_seconds: number;
}

export interface UpdateJitterSettingsPayload {
  min_seconds: number;
  max_seconds: number;
}
