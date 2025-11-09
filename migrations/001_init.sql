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

-- Main table in meta schema
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
  owner            TEXT NULL,
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
