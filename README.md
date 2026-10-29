# Trilha USP — MVP

Plataforma de conhecimento colaborativo da EACH-USP. Monólito **Django** (templates no servidor, reaproveitando o HTML/CSS do site), **PostgreSQL**, hospedagem gratuita (Render + Neon).

## O que existe
- Páginas do site (início, módulos, sobre, documentação, contato, **privacidade**, **termos de uso**).
- Login por link no e-mail `@usp.br` (sem senha, uso único, expira em 15 min) com limites por e-mail, por IP e global.
- Perfil mínimo (nome de exibição + semestre de ingresso, **travado depois do 1º preenchimento**), **exportação dos próprios dados (JSON)** e **exclusão de conta**.
- Disciplinas: lista com busca, detalhe, nota de dificuldade 1–5 (até 3 atualizações, à prova de envios simultâneos), resumos/dicas com selo, **paginação**, **denúncia de conteúdo**.
- Moderação no painel admin: grupo **Moderadores** (selo, ocultar, excluir resumos; ver e tratar denúncias). Moderador **não vê e-mails** e **não edita o texto** dos alunos; toda ação fica registrada.
- Contato gravado no banco, com limites e aviso opcional por e-mail.
- `/healthz` (testa o banco), `robots.txt`, `sitemap.xml`.

**Fora do MVP:** upload de arquivos, atestado com IA, Senha Única, módulos além de Disciplinas.

## Rodar localmente
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # tem hashes; use --require-hashes se quiser garantir
cp .env.example .env                     # DEBUG=true; sem DATABASE_URL usa SQLite local
python manage.py migrate
python manage.py seed_demo               # dados FICTÍCIOS (só com DEBUG=true; e-mails @demo.invalid)
python manage.py createsuperuser
python manage.py runserver               # o link de login aparece no terminal
```

## Testes
```bash
DEBUG=true python manage.py test                                   # SQLite
DATABASE_URL=postgresql://... DEBUG=true python manage.py test     # PostgreSQL (inclui o teste de corrida)
```
O CI (`.github/workflows/ci.yml`) roda testes, flake8, `makemigrations --check` e `pip-audit` a cada push.

## Variáveis de ambiente (produção)
| Variável | Para quê |
|---|---|
| `DEBUG=false`, `SECRET_KEY` | obrigatórias; a chave precisa ter 32+ caracteres e não pode ser de exemplo |
| `DATABASE_URL` | conexão do app com o PostgreSQL (`?sslmode=require`) |
| `MIGRATE_DATABASE_URL` | opcional: conexão do dono do banco, usada só no build para migrar |
| `ADMIN_URL` | caminho do painel (ex.: `gestao-x7k2p9`); **não deixe `admin`** |
| `EMAIL_BACKEND=contas.email_backends.BrevoEmailBackend`, `BREVO_API_KEY`, `DEFAULT_FROM_EMAIL` | e-mail do link de login (o Render grátis bloqueia SMTP) |
| `TRUSTED_PROXY_HOPS` | veja "IP do cliente" abaixo |
| `CONTATO_NOTIFICAR` | opcional: e-mail que recebe aviso de nova mensagem de contato |
| `SENTRY_DSN` | opcional: alerta de erros (se usar, cite o Sentry na página de privacidade) |
| limites (`LOGIN_IP_MAX_PER_HOUR`, `LOGIN_GLOBAL_MAX_PER_DAY`, `PUBLICAR_MAX_POR_HORA`…) | ver `config/settings.py` |

## Painel administrativo e moderadores
- Contas **staff** (moderador/superusuário) **não entram pelo link do e-mail**: usam o login do painel (`/<ADMIN_URL>/`) com **senha**. Defina a senha com `python manage.py changepassword email@usp.br` (ou pela tela de usuários).
- O painel bloqueia por 15 min após 5 senhas erradas para o mesmo e-mail ou 10 do mesmo IP.
- Para criar um moderador: o aluno entra uma vez no site; no painel, abra o usuário, marque **moderador/admin**, adicione ao grupo **Moderadores** e defina a senha.
- Em **Tokens de login** (só superusuário) você acompanha se os e-mails estão saindo (`enviado`/`falhou`).

## IP do cliente (calibrar uma vez após o deploy)
Os limites por IP usam o cabeçalho `X-Forwarded-For`. Depois do primeiro deploy, abra a tela de login e veja nos **Logs** do Render a linha `X-Forwarded-For com N entrada(s)`. Defina `TRUSTED_PROXY_HOPS=N` (padrão 1). Se o número estiver errado, o limite por IP perde eficácia (o limite global diário continua protegendo a cota do Brevo).

## Banco: papel com menor privilégio (recomendado)
Depois de migrar, rode `scripts/neon_app_role.sql` como dono do banco (instruções no cabeçalho do arquivo), use a conexão do papel `trilha_app` em `DATABASE_URL` e a do dono em `MIGRATE_DATABASE_URL`.

## Backup e restauração
```bash
DATABASE_URL=<conexão DIRETA> ./scripts/backup.sh                    # gera o .dump
DATABASE_URL_RESTAURO=<banco vazio de teste> ./scripts/restore_check.sh arquivo.dump   # restaura e mostra contagens
```
O pg_dump precisa ser da mesma versão (ou mais nova) que o servidor. `.github/workflows/backup.yml` faz o backup semanal (segredo `DATABASE_URL`; variável opcional `PG_MAJOR`). **Faça um backup manual e um teste de restauração antes de abrir para a turma.** Antes de qualquer migração que apague colunas ou tabelas, faça backup.

## Dependências
`requirements.in` lista as diretas; `requirements.txt` é o lockfile com hashes. Para atualizar: instale `requirements.in` num venv limpo, rode `pip freeze` e regenere os hashes (ou use `pip-compile --generate-hashes`). O Dependabot abre PRs semanais.

## Privacidade e LGPD
As páginas `/privacidade/` e `/termos/` descrevem o tratamento atual. **O texto precisa de revisão por quem tenha competência jurídica** (base legal, controlador, prazos) antes do lançamento público. Se mudar de prestador ou coletar novos dados, atualize a página.

## Retenção
Tokens de login: 7 dias · limites de abuso: 2 dias · sessões expiradas: limpas automaticamente · mensagens de contato: 12 meses. A limpeza roda de forma oportunista (a cada ~50 pedidos de login); manualmente: `python manage.py shell -c "from contas import limites; print(limites.limpar_antigos())"`.

## Estrutura
```
config/       settings, urls, middleware (CSP), admin_site (bloqueio de força bruta)
core/         páginas, contato, privacidade/termos, healthz, robots, sitemap
contas/       usuário (e-mail), login por link, perfil, limites de abuso, envio de e-mail
disciplinas/  catálogo, resumos, notas, denúncias, regras, admin
templates/    base.html + páginas
static/       CSS/JS originais, app.css/app.js, fontes locais, pdf.js local, docs/, img/
scripts/      backup, restauração, papel de banco
```
