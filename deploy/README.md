# Deploy de produção do XHub

Registro da topologia real de produção (VPS única, 2026-07-22).
Domínio: `xhub.app.br` (+ `www.xhub.app.br`).

## Topologia

```
Internet (443/80)
   │
   ▼
Nginx (host, fora do Docker)
   ├── / (arquivos estáticos)  →  /opt/xhub/frontend/dist
   └── /api/ (reverse proxy)   →  http://127.0.0.1:8000 (container backend)

Docker Compose (docker-compose.prod.yml)
   ├── db       (Postgres 16, sem porta publicada — só rede interna)
   └── backend  (FastAPI, publicado só em 127.0.0.1:8000)
```

Sem container de frontend em produção: o build estático (`npm run
build`) é gerado por um container Node descartável e servido
diretamente pelo Nginx do host — mais simples que manter um container
rodando só para servir arquivos estáticos.

## Servidor

- VPS: Ubuntu 24.04 LTS, IP `2.25.183.33`.
- SSH: só chave pública (`PasswordAuthentication no`,
  `PermitRootLogin prohibit-password` — ver
  `/etc/ssh/sshd_config.d/10-xhub-hardening.conf`).
- Firewall: `ufw`, só 22 (SSH), 80 (HTTP, redireciona pra 443) e 443
  (HTTPS) liberados.
- Código em `/opt/xhub`, clonado do GitHub (`4lusz/Xhub`) — atualizar
  com `git pull` + rebuild (ver "Atualizando" abaixo).

## Segredos de produção

`/opt/xhub/backend/.env` (nunca versionado, `chmod 600`) — gerado uma
vez no deploy inicial: `JWT_SECRET_KEY`/`TOKEN_ENCRYPTION_KEY` novos e
exclusivos de produção (nunca os mesmos valores de desenvolvimento
local), `X_CLIENT_ID`/`X_CLIENT_SECRET`/`GROQ_API_KEY` reaproveitados
do app já existente, `ENVIRONMENT=production` (ativa a validação
estrita de segredo forte em `app/config/settings.py`),
`TRUST_PROXY_HEADERS=true` (necessário porque o Nginx é um proxy
confiável na frente do backend — sem isso, o rate limiter veria sempre
o IP do Nginx, nunca o do cliente real).

## ATENÇÃO: X-Forwarded-For deve ser SOBRESCRITO, nunca concatenado

`proxy_set_header X-Forwarded-For $remote_addr;` — de propósito, **não**
`$proxy_add_x_forwarded_for` (o padrão comum em tutoriais genéricos de
Nginx, que só *acrescenta* o IP real ao que o cliente já mandou, em vez
de substituir).

**Causa raiz de uma vulnerabilidade real encontrada e corrigida em
produção (2026-07-22, auditoria pós-deploy):** com
`TRUST_PROXY_HEADERS=true` (necessário aqui, ver acima) e
`$proxy_add_x_forwarded_for`, um cliente que manda seu próprio header
`X-Forwarded-For: <qualquer coisa>` tinha esse valor preservado como o
**primeiro** item da lista repassada ao backend — e
`RateLimitMiddleware._client_key` usa exatamente o primeiro item. Como
o valor era escolhido livremente pelo cliente, bastava variar esse
header a cada requisição para contornar completamente o rate limit do
login (confirmado ao vivo: 20 tentativas com 20 IPs falsos diferentes,
zero bloqueadas). Corrigido sobrescrevendo o header com `$remote_addr`
(a conexão TCP real, que o cliente não controla) — reconfirmado ao
vivo: mesmo teste, exatamente 10 bloqueadas de 20 (o limite
configurado). Ver `docs/AUDITORIA_SEGURANCA.md` para o registro
completo.

## HTTPS

Certificado Let's Encrypt via `certbot --nginx`, renovação automática
já agendada pelo próprio certbot (systemd timer). Nunca editar os
blocos marcados `# managed by Certbot` em
`/etc/nginx/sites-available/xhub.conf` manualmente.

## Backup

`/opt/xhub/backup-db.sh` (cron diário às 3h,
`/etc/cron.d/xhub-backup`) — `pg_dump` comprimido em
`/opt/xhub/backups/`, retenção de 14 dias. Restaurar:
```bash
gunzip -c /opt/xhub/backups/xhub_TIMESTAMP.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db psql -U xhub xhub
```

## Atualizando o deploy (nova versão)

```bash
cd /opt/xhub
git pull origin main
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# Frontend (só se algo em frontend/ mudou):
docker run --rm -v /opt/xhub/frontend:/app -w /app \
  -e VITE_API_URL=https://xhub.app.br/api/v1 \
  node:20-alpine sh -c "npm ci && npm run build"
```

## Callback OAuth do X

O app registrado no X Developer Portal precisa ter
`https://xhub.app.br/api/v1/oauth/x/callback` na lista de "Callback
URI / Redirect URL" autorizadas — sem isso, a conexão de contas do X
falha com erro de redirect_uri inválido.
