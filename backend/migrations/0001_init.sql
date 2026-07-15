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

CREATE TABLE memberships (
    tenant_id  uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role       text NOT NULL CHECK (role IN ('counsellor', 'admin', 'employee')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE tenant_invites (
    code_hash  text PRIMARY KEY,
    tenant_id  uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    role       text NOT NULL CHECK (role IN ('counsellor', 'admin', 'employee')),
    created_by uuid REFERENCES users (id) ON DELETE SET NULL,
    expires_at timestamptz NOT NULL,
    used_by    uuid REFERENCES users (id) ON DELETE SET NULL,
    used_at    timestamptz
);

-- ---------------------------------------------------------------------------
-- Letters, shares and messages
-- ---------------------------------------------------------------------------

CREATE TABLE letters (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    status      text NOT NULL CHECK (status IN ('received', 'processing', 'ready', 'failed')),
    letter_type text,
    language    text NOT NULL,
    state       bytea NOT NULL,            -- encrypted PipelineState
    image_keys  text[] NOT NULL DEFAULT '{}',
    degraded    boolean NOT NULL DEFAULT false,
    error       text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL
);
CREATE INDEX letters_owner_created ON letters (owner_id, created_at DESC);
CREATE INDEX letters_expires ON letters (expires_at);

CREATE TABLE shares (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    letter_id             uuid NOT NULL REFERENCES letters (id) ON DELETE CASCADE,
    owner_id              uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    tenant_id             uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    consent_text_version  text NOT NULL,
    consented_at          timestamptz NOT NULL DEFAULT now(),
    expires_at            timestamptz NOT NULL,
    revoked_at            timestamptz,
    case_status           text NOT NULL DEFAULT 'new' CHECK (case_status IN ('new', 'in_progress', 'closed')),
    assigned_to           uuid REFERENCES users (id) ON DELETE SET NULL,
    client_language       text NOT NULL,
    created_at            timestamptz NOT NULL DEFAULT now(),
    UNIQUE (letter_id, tenant_id)
);
CREATE INDEX shares_tenant_status ON shares (tenant_id, case_status, created_at DESC);

CREATE TABLE messages (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    share_id    uuid NOT NULL REFERENCES shares (id) ON DELETE CASCADE,
    author_id   uuid REFERENCES users (id) ON DELETE SET NULL,
    author_role text NOT NULL CHECK (author_role IN ('client', 'counsellor')),
    body        bytea NOT NULL,            -- encrypted {text, translations}
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX messages_share ON messages (share_id, created_at);

-- ---------------------------------------------------------------------------
-- Operations: cost ledger, quotas, rate limits, idempotency, audit, billing
-- ---------------------------------------------------------------------------

CREATE TABLE llm_calls (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at     timestamptz NOT NULL DEFAULT now(),
    task           text NOT NULL,
    provider       text NOT NULL,
    model          text NOT NULL,
    prompt_version text NOT NULL,
    input_tokens   int NOT NULL,
    output_tokens  int NOT NULL,
    list_price_usd numeric(12, 6) NOT NULL,
    latency_ms     int NOT NULL,
    attempts       int NOT NULL,
    fallback_used  boolean NOT NULL,
    ok             boolean NOT NULL,
    error          text,
    user_id        uuid,                   -- no FK: the ledger outlives deleted users
    letter_id      uuid
);
CREATE INDEX llm_calls_created ON llm_calls (created_at);
CREATE INDEX llm_calls_user_day ON llm_calls (user_id, created_at);

CREATE TABLE usage_counters (
    user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    period  text NOT NULL,                 -- YYYY-MM
    letters int NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, period)
);

CREATE TABLE rate_limits (
    key          text NOT NULL,
    window_start timestamptz NOT NULL,
    count        int NOT NULL,
    PRIMARY KEY (key, window_start)
);

CREATE TABLE idempotency_keys (
    user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    key        text NOT NULL,
    response   jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, key)
);

CREATE TABLE audit_log (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    at          timestamptz NOT NULL DEFAULT now(),
    actor_id    uuid,
    tenant_id   uuid,
    action      text NOT NULL,
    target_type text NOT NULL,
    target_id   text NOT NULL,
    details     jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX audit_log_tenant ON audit_log (tenant_id, at DESC);

CREATE TABLE billing_events (
    provider    text NOT NULL,
    event_id    text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, event_id)
);

-- ---------------------------------------------------------------------------
-- Grants
-- ---------------------------------------------------------------------------

GRANT USAGE ON SCHEMA public TO letterlens_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON
    users, user_keys, tenants, memberships, tenant_invites, letters, shares, messages,
    usage_counters, rate_limits, idempotency_keys, billing_events
TO letterlens_app;
GRANT SELECT, INSERT ON llm_calls TO letterlens_app;
-- The audit log is append-only for the application.
GRANT SELECT, INSERT ON audit_log TO letterlens_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO letterlens_app;

-- ---------------------------------------------------------------------------
-- Row-level security
-- ---------------------------------------------------------------------------

