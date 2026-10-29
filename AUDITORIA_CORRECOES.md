# Correções da auditoria de 27/10/2026

| ID | Achado | Situação | Como foi tratado / como verificar |
|---|---|---|---|
| SEC-001 | Login sem limite por IP/global; e-mail síncrono | **Corrigido** | Limites por e-mail, IP e global; envio em segundo plano; gunicorn com threads. Teste de ataque: 30 pedidos → 10 e-mails; home responde em 0,04 s durante o ataque (antes 22,9 s) |
| SEC-002 | Staff entra só por link; admin sem lockout | **Corrigido** (TOTP não implementado) | Staff exige senha no painel; bloqueio após 5/10 falhas; caminho configurável (`ADMIN_URL`) |
| PRIV-001 | Sem privacidade/termos; Google Fonts/jsDelivr; sem exclusão | **Corrigido no código; texto precisa de revisão jurídica** | Páginas, exportação e exclusão de conta, fontes e pdf.js locais; rodapé sem afirmação de conformidade |
| DATA-001 | Backup/restauração não comprovados | **Scripts prontos; falta executar no Neon (ação sua)** | `scripts/backup.sh`, `restore_check.sh` (testados em PostgreSQL local), workflow semanal (não testado no GitHub) |
| ABU-001 | Sem limite em publicar/contato; sem denúncia | **Corrigido** | Limites por usuário/IP/e-mail; denúncias com painel; aviso opcional de contato |
| OPS-001 | Health check sem banco; falha de e-mail silenciosa; sem monitor | **Corrigido em parte** | `/healthz` (503 sem banco); status `enviado/falhou` visível no admin; Sentry opcional. Falta contratar monitor externo (ação sua) |
| DEP-001 | Dependências sem trava; sem CI | **Corrigido em parte** | Lockfile com hashes, CI, Dependabot. Falta ativar proteção da `main` no GitHub (ação sua) |
| PRIV-002 | Retenção indefinida; e-mail visível a moderadores | **Corrigido** | Limpeza automática; moderador vê só o nome de exibição |
| GOV-001 | Ingresso editável; moderador edita texto; sem trilha | **Corrigido** | Ingresso travado; moderador só dá selo/oculta; ações geram registro |
| FUNC-001 | Conteúdo fictício em página pública | **Resolvido** | Entidades virou «em breve» (sua alteração); rótulo do card do Canvas corrigido |
| TEST-001 | Cobertura incompleta | **Ampliado** | 113 testes (SQLite e PostgreSQL) + testes em navegador real (Firefox headless) e axe |
| BIZ-001 | Corrida na avaliação (500) | **Corrigido** | Transação com bloqueio de linha; teste com 20 envios simultâneos em PostgreSQL |
| SEC-003 | Sem CSP/Permissions-Policy; scripts inline; CDN | **Corrigido** | CSP restritiva (sem `unsafe-inline` em scripts), pdf.js local; painel admin fora da CSP |
| INFRA-001 | Papel do banco com privilégio total | **Script pronto; falta aplicar no Neon (ação sua)** | `scripts/neon_app_role.sql` (validado em PostgreSQL local) |
| PERF-001 | Cache/compressão | **Melhorado** | gzip no HTML (16,6 KB → 4,2 KB), cache de 1 h nos estáticos, sem fontes de terceiros. Lighthouse no site real continua pendente |
| CFG-001 | `.env.example` com chave de exemplo | **Corrigido** | Chave vazia no exemplo; app recusa chaves curtas/de exemplo em produção |
| SEO-001 | Sem robots/sitemap/canonical | **Corrigido** | robots.txt, sitemap.xml, canonical, Open Graph, noindex no login |
| A11Y-001 | Acessibilidade não medida | **Medido e corrigido (contraste)** | axe-core: único problema era o contraste do texto secundário; cor ajustada. Leitor de tela real não testado |
| OPS-002 | Migrações sem backup/rollback | **Documentado** | README: backup antes de migrações destrutivas; `MIGRATE_DATABASE_URL` |
| CODE-001 | Avisos de lint/bandit | **Corrigido** | flake8 limpo; URL do Brevo exige https |
| UX-001 / UX-002 | URL com maiúsculas; sem paginação | **Corrigido** | Redireciona para maiúsculas; 10 resumos por página |
| SEC-004 / SEC-005 | HSTS curto; confiança no proxy | **Mantido por decisão** | HSTS sobe gradualmente (README); proxy documentado |
