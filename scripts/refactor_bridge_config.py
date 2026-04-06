#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = [
    ROOT / "scripts" / "bridge_feishu_to_oris.py",
    ROOT / "scripts" / "openclaw_bridge_to_oris.py",
    ROOT / "scripts" / "feishu_send_executor_skeleton.py",
]

def patch_bridge_file(path: Path):
    text = path.read_text(encoding="utf-8")

    if "from scripts.lib.runtime_config import" in text:
        print(f"already patched: {path}")
        return

    text = text.replace(
        "from pathlib import Path\n",
        "from pathlib import Path\nfrom scripts.lib.runtime_config import local_service_url, rel_path, read_oris_api_key, exact_reply_patterns, role_routing, read_feishu_creds, feishu_api, default_source\n"
    )

    text = text.replace(
        'SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"\n',
        ''
    )
    text = text.replace(
        'OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"\n',
        ''
    )

    text = text.replace(
        'LOG_PATH = ROOT / "orchestration" / "bridge_feishu_log.jsonl"\n',
        'LOG_PATH = rel_path("bridge_feishu_log")\n'
    )
    text = text.replace(
        'LOG_PATH = ROOT / "orchestration" / "openclaw_bridge_log.jsonl"\n',
        'LOG_PATH = rel_path("openclaw_bridge_log")\n'
    )
    text = text.replace(
        'LOG_PATH = ROOT / "orchestration" / "feishu_send_executor_log.jsonl"\n',
        'LOG_PATH = rel_path("feishu_send_executor_log")\n'
    )

    text = text.replace(
        'LOCAL_V1_INFER_URL = "http://127.0.0.1:8788/v1/infer"\n',
        'LOCAL_V1_INFER_URL = local_service_url("oris_v1_infer_url")\n'
    )

    text = text.replace(
        'TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"\n',
        'TOKEN_URL = feishu_api("token_url")\n'
    )
    text = text.replace(
        'SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages"\n',
        'SEND_URL = feishu_api("send_url")\n'
    )
    text = text.replace(
        'REPLY_URL_TEMPLATE = "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"\n',
        'REPLY_URL_TEMPLATE = feishu_api("reply_url_template")\n'
    )

    text = text.replace(
        'api_key = read_api_key()\n',
        'api_key = read_oris_api_key()\n'
    )

    text = text.replace(
        'ap.add_argument("--source", default="feishu_bridge_core")\n',
        'ap.add_argument("--source", default=default_source("feishu_bridge"))\n'
    )
    text = text.replace(
        'ap.add_argument("--source", default="openclaw_bridge")\n',
        'ap.add_argument("--source", default=default_source("openclaw_bridge"))\n'
    )

    text = text.replace(
        "    t = (text or \"\").strip().lower()\n\n    coding_keywords = [\n        \"代码\", \"报错\", \"debug\", \"bug\", \"python\", \"javascript\", \"typescript\",\n        \"fastapi\", \"接口\", \"api\", \"脚本\", \"deploy\", \"nginx\", \"systemd\", \"sql\"\n    ]\n    report_keywords = [\n        \"报告\", \"洞察\", \"分析\", \"研报\", \"复盘\", \"总结\", \"report\", \"insight\"\n    ]\n    cn_keywords = [\n        \"国产\", \"中文模型\", \"阿里\", \"腾讯\", \"智谱\", \"混元\", \"百炼\", \"qwen\", \"glm\"\n    ]\n    cheap_keywords = [\n        \"省钱\", \"便宜\", \"低成本\", \"免费\", \"fallback\", \"控成本\"\n    ]\n",
        "    t = (text or \"\").strip().lower()\n    routing = role_routing()\n    coding_keywords = routing.get(\"coding_keywords\", [])\n    report_keywords = routing.get(\"report_keywords\", [])\n    cn_keywords = routing.get(\"cn_keywords\", [])\n    cheap_keywords = routing.get(\"cheap_keywords\", [])\n"
    )

    text = text.replace(
        "    patterns = [\n        r'^\\s*请只回答[：:]\\s*(.+?)\\s*$',\n        r'^\\s*只回答[：:]\\s*(.+?)\\s*$',\n        r'^\\s*请只回复[：:]\\s*(.+?)\\s*$',\n        r'^\\s*只回复[：:]\\s*(.+?)\\s*$',\n        r'^\\s*请只输出[：:]\\s*(.+?)\\s*$',\n        r'^\\s*只输出[：:]\\s*(.+?)\\s*$',\n    ]\n",
        "    patterns = exact_reply_patterns()\n"
    )

    text = text.replace(
        "def read_api_key():\n    if not SECRETS_PATH.exists():\n        return None\n    data = load_json(SECRETS_PATH)\n    return (((data.get(\"services\") or {}).get(\"oris_api\") or {}).get(\"bearerToken\"))\n\n",
        ""
    )

    text = text.replace(
        "def deep_get(data, path):\n    cur = data\n    for key in path:\n        if not isinstance(cur, dict) or key not in cur:\n            return None\n        cur = cur[key]\n    return cur\n\n",
        ""
    )

    # remove local feishu creds reader if present
    start = text.find("def read_feishu_creds():\n")
    if start != -1:
        end = text.find("\ndef post_json(", start)
        if end != -1:
            text = text[:start] + text[end+1:]

    path.write_text(text, encoding="utf-8")
    print(f"patched: {path}")

def main():
    for p in FILES:
        if p.exists():
            patch_bridge_file(p)

if __name__ == "__main__":
    main()
