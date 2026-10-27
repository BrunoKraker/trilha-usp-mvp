# Trilha USP — MVP

Plataforma de conhecimento colaborativo da EACH-USP. Monólito **Django** (templates no servidor, reaproveitando o HTML/CSS do site), **PostgreSQL**, hospedagem gratuita.

## O que já funciona (etapas 1–6)
- Páginas do site (início, módulos, sobre, entidades, documentação, contato) servidas como templates, com o mesmo visual.
- Login por link no e-mail `@usp.br` (sem senha, link de uso único, expira em 15 min, máx. 5 pedidos/hora por e-mail).
- Perfil mínimo (nome de exibição + semestre de ingresso).
- Disciplinas: lista com busca, detalhe, média de dificuldade (1–5), resumos/dicas, selo de verificado.
- Regras: só contribui quem já passou do semestre da disciplina; 1 nota por aluno (até 3 atualizações); visitante lê título/autor/selo, o texto exige login (`RESUMOS_PUBLICOS=true` abre).
- Moderação no `/admin/`: grupo **Moderadores** (só resumos: selo, ocultar, excluir). Catálogo e usuários: só superusuário.
- Formulário de contato grava no banco (visível no `/admin/`).

**Fora do MVP:** upload de arquivos, atestado com IA, Senha Única, módulos além de Disciplinas (Entidades e "Em breve" são conteúdo estático), denúncia de conteúdo.

## Rodar localmente
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # DEBUG=true; sem DATABASE_URL usa SQLite local
python manage.py migrate
python manage.py seed_demo      # dados FICTÍCIOS (só com DEBUG=true)
python manage.py createsuperuser
python manage.py runserver      # o link de login aparece no terminal
```
Contas de demonstração: `veterano@usp.br`, `calouro@usp.br`, `moderador@usp.br` (entre pelo fluxo de link; o e-mail é impresso no terminal).

## Testes
```bash
DEBUG=true python manage.py test      # 40 testes
DATABASE_URL=postgresql://... DEBUG=true python manage.py test   # contra PostgreSQL
```

## Catálogo real de disciplinas
Edite um CSV (modelo em `data/disciplinas_exemplo.csv`: `codigo,nome,semestre,creditos,obrigatoria,ementa`) e rode:
```bash
python manage.py importar_disciplinas data/minhas_disciplinas.csv
```
É idempotente (reimportar atualiza). Também dá para cadastrar pelo `/admin/`. Semestre vazio = optativa.

## Link de login manual (quando o e-mail falhar)
```bash
python manage.py gerar_link aluno@usp.br --base-url https://SEU-SITE.onrender.com
```
Rode com `DATABASE_URL` apontando para o banco de produção. O link vale 15 minutos e só uma vez.

## Moderadores
No `/admin/` > Usuários: marque **"moderador/admin"** e adicione ao grupo **Moderadores**.

## Publicar (Render grátis + Neon grátis)
1. **Neon**: crie o projeto, copie a connection string (`?sslmode=require`) → `DATABASE_URL`.
2. **E-mail (Brevo, via API)**: o Render grátis **bloqueia SMTP** (portas 25/465/587), então Gmail por SMTP não funciona. Crie conta no Brevo, verifique um remetente, gere uma chave de API → `BREVO_API_KEY`, `DEFAULT_FROM_EMAIL`, `EMAIL_BACKEND=contas.email_backends.BrevoEmailBackend`.
3. **GitHub**: suba este repositório (o `.env` está no `.gitignore`).
4. **Render**: New > Blueprint apontando para o repositório (`render.yaml`). Preencha as variáveis marcadas como "sync: false" (`DATABASE_URL`, `BREVO_API_KEY`, `DEFAULT_FROM_EMAIL`). O build roda `./build.sh` (instala, coleta estáticos, migra).
5. Crie o superusuário: no Render, aba *Shell* (pode exigir plano pago; alternativa: rode `createsuperuser` localmente com `DATABASE_URL` do Neon).
6. Importe o catálogo (comando acima, também apontando `DATABASE_URL` para o Neon).
7. Teste o login com um e-mail `@usp.br` **real** e confira se o link chega (e não cai no spam).

Variáveis: ver `.env.example`. Em produção `DEBUG=false` e `SECRET_KEY` obrigatória (o app não sobe sem ela).

## Atualizar
`git push` na branch principal → o Render refaz o deploy e aplica migrações automaticamente. Para voltar versão: *Manual Deploy* de um commit anterior no Render.

## Backup e restauração
```bash
DATABASE_URL=<conexão DIRETA do Neon, não a "pooled"> ./scripts/backup.sh
pg_restore --no-owner -d "<banco vazio>" arquivo.dump
```
Há também `.github/workflows/backup.yml` (backup semanal como artefato; precisa do segredo `DATABASE_URL`).

## Monitoramento
- Erros: *Logs* do Render (o app escreve no stdout; não registra links de login nem senhas).
- Consumo: painel do Neon (armazenamento e CU-horas) e do Render (horas de instância).
- Plano grátis do Render: o serviço dorme após 15 min sem acesso; a 1ª visita demora cerca de 1 min.

## Estrutura
```
config/       settings (tudo por variáveis de ambiente), urls
core/         páginas estáticas e formulário de contato
contas/       usuário (e-mail), login por link, perfil
disciplinas/  catálogo, resumos, avaliações, regras, admin, comandos
templates/    base.html + páginas (convertidas do HTML original)
static/       CSS/JS originais, app.css (complementos), docs/, img/
```
