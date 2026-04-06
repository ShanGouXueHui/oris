CREATE SCHEMA IF NOT EXISTS insight;
SET search_path TO insight,public;

ALTER TABLE IF EXISTS delivery_task
  ADD COLUMN IF NOT EXISTS delivery_code text,
  ADD COLUMN IF NOT EXISTS max_downloads integer DEFAULT 3,
  ADD COLUMN IF NOT EXISTS used_count integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS issued_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_downloaded_at timestamptz,
  ADD COLUMN IF NOT EXISTS revoked_at timestamptz,
  ADD COLUMN IF NOT EXISTS revoke_reason text,
  ADD COLUMN IF NOT EXISTS download_url text;

UPDATE delivery_task
SET used_count = 0
WHERE used_count IS NULL;

UPDATE delivery_task
SET max_downloads = 3
WHERE max_downloads IS NULL;

WITH ranked AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY artifact_id, channel_type
      ORDER BY id DESC
    ) AS rn
  FROM delivery_task
  WHERE status = 'pending'
    AND (revoked_at IS NULL)
)
DELETE FROM delivery_task d
USING ranked r
WHERE d.id = r.id
  AND r.rn > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_delivery_task_delivery_code
ON delivery_task(delivery_code)
WHERE delivery_code IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_delivery_task_pending_artifact_channel
ON delivery_task(artifact_id, channel_type)
WHERE status = 'pending' AND revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS download_event (
  id bigserial PRIMARY KEY,
  artifact_id bigint,
  delivery_task_id bigint,
  artifact_code text,
  delivery_code text,
  channel_type text,
  client_ip text,
  user_agent text,
  request_path text,
  request_query text,
  status text NOT NULL DEFAULT 'success',
  detail_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  downloaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_download_event_artifact_id
ON download_event(artifact_id);

CREATE INDEX IF NOT EXISTS idx_download_event_delivery_task_id
ON download_event(delivery_task_id);

CREATE INDEX IF NOT EXISTS idx_download_event_downloaded_at
ON download_event(downloaded_at DESC);

INSERT INTO insight_schema_version(version_num, version_name, applied_at)
SELECT 2, 'insight_schema_v2_download_security', now()
WHERE NOT EXISTS (
  SELECT 1
  FROM insight_schema_version
  WHERE version_num = 2
);
