# INSIGHT_POSTGRES_BOOTSTRAP

## 当前连接参数
- driver: postgresql
- host: 127.0.0.1
- port: 5432
- database: oris_insight
- schema: insight
- user: oris_app
- password: 存放在 /home/admin/.openclaw/secrets.json

## 配置文件
- config/insight_storage.json

## 初始化 SQL
- sql/insight_schema_v1.sql

## 验证命令
先读取密码，再验证 schema 表是否存在：

DB_PASSWORD=$(python3 - <<'PY2'
import json
from pathlib import Path
data = json.loads((Path('/home/admin/.openclaw/secrets.json')).read_text(encoding='utf-8'))
print(data['postgres']['oris_insight']['password'])
PY2
)

PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -U oris_app -d oris_insight -c "SET search_path TO insight,public; SELECT table_name FROM information_schema.tables WHERE table_schema='insight' ORDER BY table_name;"

## 后续下一步
1. 把 report artifact 流程接到 report_artifact / delivery_task
2. 建第一批 ORIS 自建 insight skill scaffold
3. 做 Feishu / Qbot 文件下载分发闭环
