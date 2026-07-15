-- LetterLens schema, version 1.
--
-- Tenant isolation is enforced by PostgreSQL row-level security (RLS).
-- The application connects as role letterlens_app, which does not own the
-- tables and has no BYPASSRLS. Every transaction sets three settings:
--   app.user_id     the current user (uuid) or empty
--   app.tenant_ids  comma-separated tenant uuids of the current user
--   app.system      'on' only in trusted background jobs (pipeline, retention)
-- Sensitive content (letter text, results, messages) is stored encrypted by the
-- application with a per-user data key (see letterlens/crypto.py).

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'letterlens_app') THEN
        CREATE ROLE letterlens_app NOLOGIN NOBYPASSRLS;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Context helpers
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION app_user_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
    SELECT nullif(current_setting('app.user_id', true), '')::uuid
$$;

