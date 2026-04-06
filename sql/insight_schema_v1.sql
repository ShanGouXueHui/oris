CREATE SCHEMA IF NOT EXISTS insight AUTHORIZATION oris_app;
SET search_path TO insight,public;

CREATE TABLE IF NOT EXISTS insight_schema_version (
  version_num INTEGER PRIMARY KEY,
  version_name TEXT NOT NULL,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO insight_schema_version (version_num, version_name)
VALUES (1, 'insight_schema_v1')
ON CONFLICT (version_num) DO NOTHING;

CREATE TABLE IF NOT EXISTS company (
  id BIGSERIAL PRIMARY KEY,
  company_code TEXT NOT NULL,
  company_name TEXT NOT NULL,
  company_name_en TEXT,
  domain TEXT,
  ticker TEXT,
  exchange TEXT,
  industry TEXT,
  region TEXT,
  is_target BOOLEAN NOT NULL DEFAULT FALSE,
  is_competitor BOOLEAN NOT NULL DEFAULT FALSE,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_company_code ON company(company_code);
CREATE INDEX IF NOT EXISTS ix_company_name ON company(company_name);

CREATE TABLE IF NOT EXISTS competitor_set (
  id BIGSERIAL PRIMARY KEY,
  set_code TEXT NOT NULL,
  set_name TEXT NOT NULL,
  target_company_id BIGINT REFERENCES company(id) ON DELETE SET NULL,
  description TEXT,
  scope_type TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_competitor_set_code ON competitor_set(set_code);

CREATE TABLE IF NOT EXISTS competitor_set_member (
  id BIGSERIAL PRIMARY KEY,
  competitor_set_id BIGINT NOT NULL REFERENCES competitor_set(id) ON DELETE CASCADE,
  company_id BIGINT NOT NULL REFERENCES company(id) ON DELETE CASCADE,
  role_type TEXT NOT NULL DEFAULT 'competitor',
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (competitor_set_id, company_id)
);

CREATE TABLE IF NOT EXISTS source (
  id BIGSERIAL PRIMARY KEY,
  source_code TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_priority INTEGER NOT NULL DEFAULT 100,
  root_domain TEXT,
  publisher TEXT,
  api_name TEXT,
  official_flag BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_source_code ON source(source_code);
CREATE INDEX IF NOT EXISTS ix_source_type_priority ON source(source_type, source_priority);

CREATE TABLE IF NOT EXISTS source_snapshot (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL REFERENCES source(id) ON DELETE RESTRICT,
  company_id BIGINT REFERENCES company(id) ON DELETE SET NULL,
  snapshot_type TEXT NOT NULL,
  snapshot_title TEXT,
  snapshot_url TEXT,
  snapshot_time TIMESTAMPTZ,
  fetch_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  content_hash TEXT,
  raw_storage_path TEXT,
  parsed_text_storage_path TEXT,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_source_snapshot_company_time ON source_snapshot(company_id, fetch_time DESC);
CREATE INDEX IF NOT EXISTS ix_source_snapshot_source_time ON source_snapshot(source_id, fetch_time DESC);

CREATE TABLE IF NOT EXISTS evidence_item (
  id BIGSERIAL PRIMARY KEY,
  source_snapshot_id BIGINT NOT NULL REFERENCES source_snapshot(id) ON DELETE CASCADE,
  company_id BIGINT REFERENCES company(id) ON DELETE SET NULL,
  evidence_type TEXT NOT NULL,
  evidence_title TEXT,
  evidence_text TEXT,
  evidence_number NUMERIC,
  evidence_unit TEXT,
  evidence_date DATE,
  confidence_score NUMERIC(6,4),
  locator_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_evidence_company_type ON evidence_item(company_id, evidence_type);
CREATE INDEX IF NOT EXISTS ix_evidence_snapshot ON evidence_item(source_snapshot_id);

CREATE TABLE IF NOT EXISTS metric_observation (
  id BIGSERIAL PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES company(id) ON DELETE CASCADE,
  metric_code TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  metric_value NUMERIC,
  metric_unit TEXT,
  period_type TEXT,
  period_start DATE,
  period_end DATE,
  observation_date DATE,
  source_snapshot_id BIGINT REFERENCES source_snapshot(id) ON DELETE SET NULL,
  evidence_item_id BIGINT REFERENCES evidence_item(id) ON DELETE SET NULL,
  normalization_rule TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_metric_company_code_date ON metric_observation(company_id, metric_code, observation_date DESC);

CREATE TABLE IF NOT EXISTS analysis_run (
  id BIGSERIAL PRIMARY KEY,
  run_code TEXT NOT NULL,
  request_id TEXT,
  analysis_type TEXT NOT NULL,
  target_company_id BIGINT REFERENCES company(id) ON DELETE SET NULL,
  competitor_set_id BIGINT REFERENCES competitor_set(id) ON DELETE SET NULL,
  input_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'created',
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_analysis_run_code ON analysis_run(run_code);

CREATE TABLE IF NOT EXISTS report_artifact (
  id BIGSERIAL PRIMARY KEY,
  artifact_code TEXT NOT NULL,
  run_id BIGINT REFERENCES analysis_run(id) ON DELETE SET NULL,
  request_id TEXT,
  artifact_type TEXT NOT NULL,
  title TEXT,
  storage_path TEXT NOT NULL,
  file_ext TEXT,
  file_size BIGINT,
  manifest_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  downloadable_flag BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_report_artifact_code ON report_artifact(artifact_code);
CREATE INDEX IF NOT EXISTS ix_report_artifact_run_id ON report_artifact(run_id);

CREATE TABLE IF NOT EXISTS citation_link (
  id BIGSERIAL PRIMARY KEY,
  request_id TEXT,
  report_id BIGINT REFERENCES report_artifact(id) ON DELETE CASCADE,
  claim_code TEXT,
  evidence_item_id BIGINT REFERENCES evidence_item(id) ON DELETE SET NULL,
  source_snapshot_id BIGINT REFERENCES source_snapshot(id) ON DELETE SET NULL,
  source_id BIGINT REFERENCES source(id) ON DELETE SET NULL,
  citation_label TEXT,
  citation_url TEXT,
  citation_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_citation_request_id ON citation_link(request_id);
CREATE INDEX IF NOT EXISTS ix_citation_report_id ON citation_link(report_id);

CREATE TABLE IF NOT EXISTS delivery_task (
  id BIGSERIAL PRIMARY KEY,
  artifact_id BIGINT NOT NULL REFERENCES report_artifact(id) ON DELETE CASCADE,
  channel_type TEXT NOT NULL,
  channel_target TEXT,
  delivery_mode TEXT,
  status TEXT NOT NULL DEFAULT 'created',
  delivery_result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  delivered_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_delivery_artifact_channel ON delivery_task(artifact_id, channel_type);

CREATE TABLE IF NOT EXISTS watch_task (
  id BIGSERIAL PRIMARY KEY,
  task_code TEXT NOT NULL,
  task_name TEXT NOT NULL,
  target_company_id BIGINT REFERENCES company(id) ON DELETE SET NULL,
  competitor_set_id BIGINT REFERENCES competitor_set(id) ON DELETE SET NULL,
  monitor_type TEXT NOT NULL,
  schedule_expr TEXT NOT NULL,
  enabled_flag BOOLEAN NOT NULL DEFAULT TRUE,
  config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_run_at TIMESTAMPTZ,
  next_run_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_watch_task_code ON watch_task(task_code);

CREATE TABLE IF NOT EXISTS alert_event (
  id BIGSERIAL PRIMARY KEY,
  watch_task_id BIGINT REFERENCES watch_task(id) ON DELETE SET NULL,
  company_id BIGINT REFERENCES company(id) ON DELETE SET NULL,
  alert_type TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'info',
  alert_title TEXT NOT NULL,
  alert_summary TEXT,
  trigger_value TEXT,
  threshold_value TEXT,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_alert_company_created ON alert_event(company_id, created_at DESC);
