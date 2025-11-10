-- Ensure meta schema exists
CREATE SCHEMA IF NOT EXISTS meta;

-- Create enum type in meta schema only if it does NOT already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_namespace n ON t.typnamespace = n.oid
        WHERE t.typname = 'attr_category' AND n.nspname = 'meta'
    ) THEN
        -- Use format() with %I to properly quote schema and type identifiers
        EXECUTE format('CREATE TYPE %I.%I AS ENUM (''entity'', ''component'', ''rule'', ''measure'', ''other'')', 'meta', 'attr_category');
    END IF;
END$$;

-- DROP  meta.attribute if exists

DROP TABLE IF EXISTS meta.attribute;

-- Main table in meta schema: create if not exists with the full shape
CREATE TABLE IF NOT EXISTS meta.attribute (
  id               BIGSERIAL PRIMARY KEY,
  namespace        TEXT NOT NULL DEFAULT 'default',
  entity           TEXT NOT NULL,
  category         meta.attr_category NOT NULL DEFAULT 'entity',
  logical_name     TEXT NOT NULL,
  physical_name    TEXT NOT NULL,
  data_type        TEXT NOT NULL,
  description      TEXT NULL,
  source_system    TEXT NULL,
  created_by       TEXT NOT NULL DEFAULT 'System',
  updated_by       TEXT NOT NULL DEFAULT 'System',
  synonyms         TEXT[] DEFAULT '{}',
  tags             JSONB DEFAULT '[]'::jsonb,
  is_active        BOOLEAN NOT NULL DEFAULT TRUE,
  version          INTEGER NOT NULL DEFAULT 1,
  hash             TEXT GENERATED ALWAYS AS (
      md5((namespace || '|' || entity || '|' || coalesce(physical_name,'') || '|' || coalesce(logical_name,''))::text)
  ) STORED,
  metadata         JSONB DEFAULT '{}'::jsonb,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Make the table fully idempotent by ensuring any missing columns are added with correct defaults
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'meta' AND table_name = 'attribute') THEN

        -- created_by
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'meta' AND table_name = 'attribute' AND column_name = 'created_by') THEN
            EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN created_by TEXT NOT NULL DEFAULT ''System''';
        ELSE
            -- ensure default exists
            BEGIN
                EXECUTE 'ALTER TABLE meta.attribute ALTER COLUMN created_by SET DEFAULT ''System''';
            EXCEPTION WHEN undefined_column THEN NULL; END;
        END IF;

        -- updated_by
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'meta' AND table_name = 'attribute' AND column_name = 'updated_by') THEN
            EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN updated_by TEXT NOT NULL DEFAULT ''System''';
        ELSE
            BEGIN
                EXECUTE 'ALTER TABLE meta.attribute ALTER COLUMN updated_by SET DEFAULT ''System''';
            EXCEPTION WHEN undefined_column THEN NULL; END;
        END IF;

        -- synonyms
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'meta' AND table_name = 'attribute' AND column_name = 'synonyms') THEN
            EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN synonyms TEXT[] DEFAULT ''{}''';
        END IF;

        -- tags
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'meta' AND table_name = 'attribute' AND column_name = 'tags') THEN
            EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN tags JSONB DEFAULT ''[]''::jsonb';
        END IF;

        -- metadata
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'meta' AND table_name = 'attribute' AND column_name = 'metadata') THEN
            EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN metadata JSONB DEFAULT ''{}''::jsonb';
        END IF;

        -- version
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'meta' AND table_name = 'attribute' AND column_name = 'version') THEN
            EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN version INTEGER NOT NULL DEFAULT 1';
        END IF;

        -- is_active
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'meta' AND table_name = 'attribute' AND column_name = 'is_active') THEN
            EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE';
        END IF;

        -- created_at
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'meta' AND table_name = 'attribute' AND column_name = 'created_at') THEN
            EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now()';
        ELSE
            BEGIN
                EXECUTE 'ALTER TABLE meta.attribute ALTER COLUMN created_at SET DEFAULT now()';
            EXCEPTION WHEN undefined_column THEN NULL; END;
        END IF;

        -- updated_at
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'meta' AND table_name = 'attribute' AND column_name = 'updated_at') THEN
            EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now()';
        ELSE
            BEGIN
                EXECUTE 'ALTER TABLE meta.attribute ALTER COLUMN updated_at SET DEFAULT now()';
            EXCEPTION WHEN undefined_column THEN NULL; END;
        END IF;

        -- hash (generated column) - add if missing. Note: adding a generated column requires PG >= 12
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'meta' AND table_name = 'attribute' AND column_name = 'hash') THEN
            BEGIN
                EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN hash TEXT GENERATED ALWAYS AS (md5((namespace || ''|'' || entity || ''|'' || coalesce(physical_name,'''') || ''|'' || coalesce(logical_name,'''') )::text)) STORED';
            EXCEPTION WHEN undefined_function THEN
                -- If server doesn't support GENERATED columns or expression, fallback to adding plain column
                EXECUTE 'ALTER TABLE meta.attribute ADD COLUMN hash TEXT';
            END;
        END IF;

    END IF;
END$$;

-- Unique indexes (safe for repeated migrations) in meta schema
DO $$
BEGIN
    -- ensure subsequent CREATE INDEX statements run with meta in search_path so
    -- unqualified index names are created in the meta schema (avoids quoting/`.` syntax issues)
    PERFORM set_config('search_path', 'meta', true);

    -- Only attempt to create indexes if the table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'meta' AND table_name = 'attribute') THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE schemaname = 'meta' AND indexname = 'uq_attr_namespace_entity_physical'
        ) THEN
            EXECUTE format('CREATE UNIQUE INDEX %I ON %I.%I (%s)', 'uq_attr_namespace_entity_physical', 'meta', 'attribute', 'namespace, entity, physical_name');
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE schemaname = 'meta' AND indexname = 'uq_attr_namespace_entity_logical'
        ) THEN
            EXECUTE format('CREATE UNIQUE INDEX %I ON %I.%I (%s)', 'uq_attr_namespace_entity_logical', 'meta', 'attribute', 'namespace, entity, logical_name');
        END IF;
    END IF;
END$$;

-- Search index in meta schema
DO $$
BEGIN
    PERFORM set_config('search_path', 'meta', true);
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'meta' AND table_name = 'attribute') THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE schemaname = 'meta' AND indexname = 'ix_attr_search_tsv'
        ) THEN
            EXECUTE format('CREATE INDEX %I ON %I.%I USING GIN (to_tsvector(''simple'', coalesce(namespace,'''') || '' '' || coalesce(entity,'''') || '' '' || coalesce(logical_name,'''') || '' '' || coalesce(physical_name,'''') || '' '' || coalesce(description,'''') ))', 'ix_attr_search_tsv', 'meta', 'attribute');
        END IF;
    END IF;
END$$;

-- Tag array index in meta schema
DO $$
BEGIN
    PERFORM set_config('search_path', 'meta', true);
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'meta' AND table_name = 'attribute') THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE schemaname = 'meta' AND indexname = 'ix_attr_tags_gin'
        ) THEN
            EXECUTE format('CREATE INDEX %I ON %I.%I USING GIN (tags)', 'ix_attr_tags_gin', 'meta', 'attribute');
        END IF;
    END IF;
END$$;

-- Synonyms array index in meta schema
DO $$
BEGIN
    PERFORM set_config('search_path', 'meta', true);
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'meta' AND table_name = 'attribute') THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE schemaname = 'meta' AND indexname = 'ix_attr_synonyms_gin'
        ) THEN
            EXECUTE format('CREATE INDEX %I ON %I.%I USING GIN (synonyms)', 'ix_attr_synonyms_gin', 'meta', 'attribute');
        END IF;
    END IF;
END$$;
