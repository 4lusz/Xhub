# Primeiro Acesso Obrigatorio - Especificacao e estado implementado

Este documento registra a especificacao oficial e o estado JA
IMPLEMENTADO do fluxo de primeiro acesso obrigatorio do XHub, seguindo
o mesmo formato de `docs/ROADMAP_MEDIA.md` e
`docs/ROADMAP_PUBLICACAO_INTELIGENTE.md`. Trate o codigo como fonte da
verdade em caso de divergencia futura.

## Objetivo

Toda conta no XHub e criada por um administrador, que define uma senha
inicial. Essa senha e sempre TEMPORARIA: no primeiro login, o usuario e
obrigado a defini-la de novo (por conta propria) antes de acessar
qualquer tela ou rota protegida do sistema. O mesmo vale apos uma
redefinicao administrativa de senha (ex.: cliente esqueceu a senha).

## Regras de negocio oficiais

- Toda conta nova nasce com `must_change_password=True`.
- O login (`POST /auth/login`) e SEMPRE aceito normalmente, mesmo com
  a senha temporaria -- a obrigatoriedade se aplica ao que acontece
  DEPOIS do login, nunca ao login em si.
- Enquanto `must_change_password=True`, NENHUMA rota protegida alem de
  `POST /auth/change-password` fica disponivel -- inclui rotas de
  cliente e de administrador (nao ha excecao por papel).
- `POST /auth/change-password` exige apenas a nova senha (minimo 8
  caracteres) e que ela seja diferente da senha atual -- nao pede a
  senha atual/temporaria de novo, pois o usuario ja provou conhece-la
  ao fazer login.
- Ao concluir a troca: a senha temporaria deixa de funcionar
  IMEDIATAMENTE (ha uma unica coluna `password_hash`, sobrescrita --
  nunca existe um estado em que as duas senhas sejam validas ao mesmo
  tempo); `must_change_password` volta a `False`; todas as sessoes
  (refresh tokens) do usuario sao revogadas, forcando qualquer sessao
  antiga a autenticar de novo.
- Redefinicao administrativa (`POST
  /admin/users/{id}/reset-password`): gera uma nova senha temporaria
  ALEATORIA (o admin nunca escolhe o valor), marca
  `must_change_password=True` de novo e revoga todas as sessoes ativas
  do usuario -- o ciclo de primeiro acesso se repete.
- O administrador nunca ve a senha ATUAL do usuario -- apenas hashes
  sao persistidos (`bcrypt`, ja era o padrao do projeto). A unica senha
  em texto puro que o admin ve e a nova senha temporaria que ele mesmo
  acabou de gerar, exibida uma unica vez na resposta HTTP.

## Arquitetura implementada

Preserva a arquitetura em camadas do XHub (`Routes -> Services ->
Repositories -> Models`) e o padrao ja existente de bloqueio de conta
(`ensure_user_not_blocked`), estendido pelo mesmo mecanismo.

### Backend

- `app/models/user.py`
  - `User.must_change_password` (bool, not null, default `True` no
    Python/ORM -- todo INSERT via `UserService.create_user` explicita
    o valor mesmo assim, por clareza no ponto de criacao da conta).
- `app/domain/contexts.py` / `app/domain/policies.py`
  - `UserContext.must_change_password`; `ensure_password_change_not_required`
    (mesma forma de `ensure_user_not_blocked` -- funcao pura, levanta
    `PasswordChangeRequiredException`).
- `app/core/exceptions.py`
  - `PasswordChangeRequiredException` -- mapeada para HTTP
    **428 Precondition Required** (RFC 6585), deliberadamente distinta
    de 401 (sessao invalida) e 403 (acesso negado) para o frontend
    saber redirecionar para a tela de troca de senha.
- `app/auth/dependencies.py`
  - `_resolve_authenticated_user`: decodifica o token, carrega o
    usuario, garante que a conta nao esta bloqueada -- SEM checar
    primeiro acesso. Usado por:
    - `get_current_user_for_password_change`: usado exclusivamente por
      `POST /auth/change-password`.
    - `get_current_user`: adiciona `ensure_password_change_not_required`
      por cima. Como `get_current_client`/`get_current_admin` dependem
      de `get_current_user`, TODA rota protegida do XHub herda a
      protecao automaticamente, sem precisar de nenhuma alteracao
      individual em cada rota.
- `app/auth/password.py`
  - `generate_temporary_password()`: senha aleatoria de 16 caracteres,
    alfabeto sem caracteres ambiguos (sem `0/O`, `1/l/I`), pensada para
    ser comunicada manualmente pelo administrador.
- `app/repositories/refresh_token_repository.py`
  - `revoke_all_for_user(user_id)`: revoga todas as sessoes ativas --
    usado tanto na conclusao do primeiro acesso quanto na redefinicao
    administrativa.
- `app/services/user_service.py`
  - `create_user`: explicita `must_change_password=True`.
  - `complete_first_access(user_id, new_password)`: troca a senha,
    valida que e diferente da atual, zera a flag, revoga sessoes.
  - `reset_password(user_id) -> (User, str)`: gera senha temporaria,
    marca a flag, revoga sessoes, retorna a senha em texto puro (nunca
    persistida nem logada).
- `app/routes/auth.py`
  - `TokenResponse`/`UserResponse` ganham `must_change_password`.
  - `POST /auth/change-password`: unica rota protegida acessivel
    durante o primeiro acesso obrigatorio.
- `app/routes/admin.py`
  - `POST /admin/users/{user_id}/reset-password`: gera senha
    temporaria, registra `AuditAction.USER_PASSWORD_RESET` (nunca com
    a senha nos detalhes do log).
- Migrations: `c3d4e5f6a7b8` (`users.must_change_password` -- usuarios
  EXISTENTES migrados com `False`, preservando o acesso normal de
  quem ja usava o sistema antes desta funcionalidade) e `d4e5f6a7b8c9`
  (`AuditAction.USER_PASSWORD_RESET` no enum nativo do Postgres).

**Decisao tecnica -- por que 428 e nao 403:** o codigo 403 ja e usado
para "acesso negado" (usuario bloqueado, papel incorreto). Reusa-lo
aqui obrigaria o frontend a inspecionar o corpo/mensagem do erro
(fragil) para distinguir "bloqueado" de "precisa trocar senha". 428
Precondition Required e semanticamente correto (uma precondicao --
senha definitiva definida -- precisa ser satisfeita antes da
requisicao prosseguir) e permite ao frontend decidir com uma unica
checagem de status.

**Decisao tecnica -- por que nao pedir a senha atual em
`change-password`:** especificacao explicita ("Campos: Nova senha,
Confirmar nova senha"); alem disso, o usuario ja provou conhecer a
senha atual/temporaria ao completar o login que precedeu esta chamada
(o endpoint exige o access token emitido nesse login).

**Decisao tecnica -- bootstrap do primeiro administrador
(`app/scripts/create_admin.py`):** tambem passa a nascer com
`must_change_password=True`, por consistencia -- `UserService.create_user`
e o unico caminho de criacao de conta no XHub, usado tanto pela API
administrativa quanto por este script CLI. O operador digita uma senha
propria via `getpass` mas ainda assim confirma/redefine no primeiro
login, comportamento uniforme e seguro por padrao em vez de um caso
especial.

### Frontend

- `types/auth.ts`, `types/user.ts`: `must_change_password` em
  `TokenResponse`/`User`; `ResetPasswordResult` (resposta da
  redefinicao administrativa).
- `stores/authStore.ts`: `mustChangePassword` persistido (localStorage,
  via zustand `persist`) -- `ProtectedRoute` precisa decidir o
  redirecionamento de forma sincrona, inclusive logo apos um F5, antes
  de qualquer chamada a `GET /auth/me` (que ficaria bloqueada com 428
  enquanto for `true`). Atualizado em todo login/refresh
  (`setTokens`) e ao concluir a troca (`setMustChangePassword(false)`).
- `services/auth.ts` / `hooks/useAuth.ts`: `changePassword` +
  `useChangePassword` (limpa a flag e navega para `/` ao suceder).
- `services/api.ts`: interceptor trata 428 como rede de seguranca
  (sincroniza a flag e redireciona), complementando -- nao
  substituindo -- o gate normal do roteamento.
- `routes/ProtectedRoute.tsx`: redireciona para `/first-access`
  enquanto `mustChangePassword=true`, e de volta para `/` se o usuario
  tentar acessar `/first-access` sem precisar (idempotente).
- `pages/FirstAccessPage.tsx`: tela dedicada, deliberadamente distinta
  do login (icone de escudo, explicacao explicita do motivo de
  seguranca, aviso de que e obrigatoria e unica) -- campos "Nova senha"
  e "Confirmar nova senha" com validacao de correspondencia.
- Admin (`components/admin/ResetPasswordResultDialog.tsx`,
  `pages/AdminUsersPage.tsx`): acao "Redefinir senha" no menu de cada
  usuario; a senha temporaria gerada e exibida uma unica vez, com
  botao de copiar; badge "Aguardando 1º acesso" na listagem.
- `components/admin/CreateUserDialog.tsx`: campo renomeado de "Senha
  inicial" para "Senha temporária", com nota explicando a troca
  obrigatoria no primeiro login.

## Validacao realizada

Ciclo completo testado via `curl` contra a API real (nao apenas testes
unitarios com dublês):

1. `POST /admin/users` -- usuario criado com `must_change_password=true`.
2. `POST /auth/login` com a senha temporaria -- aceito normalmente,
   `must_change_password=true` no corpo da resposta.
3. `GET /auth/me`, `GET /twitter-accounts`, `GET /posts` com o token
   dessa sessao -- todos `428`, mesma mensagem.
4. `POST /auth/change-password`:
   - com a mesma senha atual -- `422` ("deve ser diferente").
   - com senha curta (< 8 chars) -- `422` (validacao Pydantic).
   - com senha valida e diferente -- `200`, `must_change_password=false`.
5. Login com a senha TEMPORARIA antiga -- `401` (nao funciona mais).
6. Login com a senha NOVA -- `200`, `must_change_password=false`;
   `GET /auth/me` e `GET /twitter-accounts` -- `200` (liberado).
7. Refresh token da sessao anterior a troca -- `401` (revogado).
8. `POST /admin/users/{id}/reset-password` -- nova senha temporaria
   gerada, `must_change_password=true`; a sessao anterior (ainda com
   access token tecnicamente valido) passa a receber `428`
   IMEDIATAMENTE (o gate le `must_change_password` fresco do banco a
   cada requisicao, nao depende de o token expirar).
9. Novo ciclo completo de primeiro acesso apos a redefinicao --
   idem passos 2-6, confirmado funcionando identicamente.
10. `GET /admin/audit-logs` -- `user_password_reset` registrado, com
    `details=null` (a senha nunca aparece no log).
11. Um usuario comum tentando chamar `POST
    /admin/users/{id}/reset-password` -- `403` (rota exclusiva de
    administrador).
12. `pytest`: 5 passaram, 1 falha pre-existente e nao relacionada
    (mesma de sessoes anteriores, dublê desatualizado de
    `SubscriptionService.to_domain_context`).
13. Frontend: `tsc --noEmit` e `npm run build` limpos; servidor de
    desenvolvimento verificado via `curl` apos restart (novos
    arquivos servidos, `ProtectedRoute`/`App.tsx` com o gate).

**Nao validado interativamente no navegador** (sem ferramenta de
automacao de browser disponivel neste ambiente) -- a tela
`FirstAccessPage` e o dialog de redefinicao administrativa foram
verificados apenas estaticamente (tipos, build, arquivo servido
corretamente). Recomenda-se um teste manual clicando na interface
antes do primeiro uso em producao.

## Fora de escopo desta implementacao

- Jitter entre publicacoes (proxima etapa do roadmap do produto, fora
  desta tarefa por instrucao explicita).
- Autoatendimento de "esqueci minha senha" pelo proprio cliente (fluxo
  de e-mail/token de recuperacao) -- a especificacao pede
  exclusivamente redefinicao ADMINISTRATIVA.
- Tela de "alterar senha" voluntaria fora do primeiro acesso (ex.: em
  Configuracoes) -- nao pedida na especificacao; o endpoint
  `POST /auth/change-password` e funcionalmente reutilizavel para isso
  no futuro, mas nenhuma UI foi construida para esse caso agora.
- Politica de complexidade de senha alem do minimo de 8 caracteres
  (mesma regra ja usada em todo o resto do projeto, preservada por
  consistencia).
