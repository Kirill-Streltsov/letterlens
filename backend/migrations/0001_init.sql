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

CREATE OR REPLACE FUNCTION app_tenant_ids() RETURNS uuid[]
LANGUAGE sql STABLE AS $$
    SELECT coalesce(
        string_to_array(nullif(current_setting('app.tenant_ids', true), ''), ',')::uuid[],
        '{}'::uuid[]
    )
$$;

CREATE OR REPLACE FUNCTION app_is_system() RETURNS boolean
LANGUAGE sql STABLE AS $$
    SELECT coalesce(current_setting('app.system', true), '') = 'on'
$$;

-- ---------------------------------------------------------------------------
-- Identity and tenants
-- ---------------------------------------------------------------------------

CREATE TABLE users (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_sub        text NOT NULL UNIQUE,
    display_name       text,
    preferred_language text NOT NULL DEFAULT 'en',
    plan               text NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'plus')),
    plan_source        text CHECK (plan_source IN ('appstore', 'stripe', 'employer', 'pilot')),
    plan_expires_at    timestamptz,
    stripe_customer_id text,
    created_at         timestamptz NOT NULL DEFAULT now()
);

-- Wrapped per-user data encryption key. Deleting the row crypto-shreds all
-- ciphertext of that user, including backups.
CREATE TABLE user_keys (
    user_id     uuid PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    wrapped_dek bytea NOT NULL,
    kek_version int NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tenants (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name               text NOT NULL,
    kind               text NOT NULL CHECK (kind IN ('counselling', 'employer')),
    city               text,
    languages          text[] NOT NULL DEFAULT '{}',
    public_listing     boolean NOT NULL DEFAULT false,
    seats              int NOT NULL DEFAULT 0 CHECK (seats >= 0),
    stripe_customer_id text,
    created_at         timestamptz NOT NULL DEFAULT now()
);

