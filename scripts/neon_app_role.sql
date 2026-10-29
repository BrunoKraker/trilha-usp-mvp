-- Papel de aplicação com MENOR PRIVILÉGIO (somente dados, sem criar/alterar tabelas).
-- Rode UMA vez, conectado como dono do banco (neondb_owner), depois das migrações:
--   psql "$MIGRATE_DATABASE_URL" -v banco=neondb -v senha="'TROQUE-POR-SENHA-FORTE'" -f scripts/neon_app_role.sql
-- (banco = nome do seu banco no Neon; o padrão costuma ser neondb)
-- Depois use a conexão deste papel em DATABASE_URL (app) e mantenha a do dono em MIGRATE_DATABASE_URL (build).
CREATE ROLE trilha_app LOGIN PASSWORD :senha;
GRANT CONNECT ON DATABASE :"banco" TO trilha_app;
GRANT USAGE ON SCHEMA public TO trilha_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trilha_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO trilha_app;
-- Tabelas criadas por migrações futuras (executadas pelo dono) já nascem com esses acessos:
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trilha_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO trilha_app;
