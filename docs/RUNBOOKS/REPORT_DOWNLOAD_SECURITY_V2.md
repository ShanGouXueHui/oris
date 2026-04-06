# REPORT_DOWNLOAD_SECURITY_V2

## 验证目标
1. 本地 health 正常
2. 公网签名下载 200
3. 控制台主页仍然 401
4. download_event 有审计记录
5. delivery_task.used_count 会增加
6. revoke 后返回 403

## 常用命令
### 重新同步 artifacts + delivery tasks
python3 scripts/register_report_delivery.py

### 撤销单个 delivery link
python3 scripts/revoke_delivery_links.py --delivery-code <delivery_code> --reason wrong_recipient

### 查看最近下载审计
python3 - <<'PY'
import json, psycopg2
cfg=json.load(open('config/insight_storage.json','r',encoding='utf-8'))
db=cfg.get('db') or cfg.get('postgres') or cfg.get('database') or (cfg.get('storage') or {}).get('db') or (cfg.get('storage') or {}).get('postgres') or (cfg.get('storage') or {}).get('database')
conn=psycopg2.connect(host=db['host'],port=db['port'],dbname=db['dbname'],user=db['user'],password=db.get('password',''))
cur=conn.cursor()
cur.execute("SET search_path TO insight,public; SELECT id,delivery_code,status,downloaded_at FROM download_event ORDER BY id DESC LIMIT 20;")
print(cur.fetchall())
cur.close(); conn.close()
PY
