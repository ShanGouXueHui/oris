#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.oris_llm_client import call_oris_text


UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def utc_now():
    return datetime.now(timezone.utc)


def utc_now_iso():
    return utc_now().isoformat()


def ts_compact():
    return utc_now().strftime("%Y%m%d_%H%M%S")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def relpath(path: Path):
    return str(path.relative_to(ROOT))


def normalize_text(text: str) -> str:
    text = (text or "").replace("\x00", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


class SimpleHTMLText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_ignored = 0
        self.current_tag = None
        self.title_parts = []
        self.body_parts = []

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in {"script", "style", "noscript"}:
            self.in_ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.in_ignored > 0:
            self.in_ignored -= 1
        self.current_tag = None

    def handle_data(self, data):
        if self.in_ignored > 0:
            return
        text = normalize_text(data)
        if not text:
            return
        if self.current_tag == "title":
            self.title_parts.append(text)
        self.body_parts.append(text)

    def result(self):
        title = normalize_text(" ".join(self.title_parts))
        body = "\n".join(self.body_parts)
        body = re.sub(r"\n{2,}", "\n", body).strip()
        return title, body


def looks_like_pdf(url: str, content_type: str, file_path: Path) -> bool:
    ct = (content_type or "").lower()
    if "application/pdf" in ct:
        return True
    if str(url or "").lower().endswith(".pdf"):
        return True
    try:
        raw = file_path.read_bytes()[:5]
        return raw == b"%PDF-"
    except Exception:
        return False


def decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(enc, errors="ignore")
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def parse_html_text(raw: bytes):
    text = decode_bytes(raw)
    parser = SimpleHTMLText()
    parser.feed(text)
    title, body = parser.result()
    return title, body, text


def extract_pdf_text(pdf_path: Path) -> str:
    txt_path = pdf_path.with_suffix(".txt")
    pdftotext = subprocess.run(
        ["pdftotext", str(pdf_path), str(txt_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if pdftotext.returncode == 0 and txt_path.exists():
        try:
            return txt_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        out = []
        for page in reader.pages[:80]:
            try:
                out.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(out)
    except Exception:
        return ""


def curl_fetch(url: str, timeout: int = 60):
    with tempfile.TemporaryDirectory(prefix="oris_direct_fetch_") as td:
        body_path = Path(td) / "body.bin"
        head_path = Path(td) / "head.txt"

        cmd = [
            "curl",
            "-L",
            "--http1.1",
            "--compressed",
            "-A", UA,
            "-H", "Accept: text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
            "-H", "Cache-Control: no-cache",
            "-H", "Pragma: no-cache",
            "--connect-timeout", "15",
            "--max-time", str(timeout),
            "-D", str(head_path),
            "-o", str(body_path),
            url,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)

        headers_text = ""
        if head_path.exists():
            headers_text = head_path.read_text(encoding="utf-8", errors="ignore")

        raw = b""
        if body_path.exists():
            raw = body_path.read_bytes()

        status_code = None
        content_type = ""
        final_url = url

        for line in headers_text.splitlines():
            m = re.match(r"HTTP/\d+(?:\.\d+)?\s+(\d+)", line.strip(), flags=re.I)
            if m:
                status_code = int(m.group(1))
            if line.lower().startswith("content-type:"):
                content_type = line.split(":", 1)[1].strip()
            if line.lower().startswith("location:"):
                final_url = line.split(":", 1)[1].strip()

        if r.returncode != 0 and not raw:
            return {
                "ok": False,
                "status_code": status_code,
                "content_type": content_type,
                "final_url": final_url,
                "title": "",
                "body_text": "",
                "raw_text": "",
                "error": (r.stderr or r.stdout or "").strip()[:1000],
            }

        # PDF
        if looks_like_pdf(url, content_type, body_path):
            body = extract_pdf_text(body_path)
            title = ""
            for line in body.splitlines():
                one = normalize_text(line)
                if len(one) >= 8:
                    title = one[:200]
                    break
            if not title:
                title = Path(url).name or "PDF Document"
            return {
                "ok": True,
                "status_code": status_code or 200,
                "content_type": content_type or "application/pdf",
                "final_url": url,
                "title": title,
                "body_text": body,
                "raw_text": "",
                "error": None,
            }

        title, body, raw_text = parse_html_text(raw)
        return {
            "ok": True,
            "status_code": status_code or 200,
            "content_type": content_type or "text/html",
            "final_url": url,
            "title": title,
            "body_text": body,
            "raw_text": raw_text,
            "error": None,
        }


NOISE_PATTERNS = [
    r"access denied",
    r"cookies?",
    r"privacy",
    r"terms",
    r"subscribe to email alerts",
    r"investor alert",
    r"unsubscribe",
    r"you don't have permission",
    r"errors\.edgesuite\.net",
]


def is_noise_text(text: str) -> bool:
    t = normalize_text(text).lower()
    if not t:
        return True
    for p in NOISE_PATTERNS:
        if re.search(p, t, flags=re.I):
            return True
    return False


PROFILE_KEYWORDS = {
    "automotive_oem": [
        "revenue", "ebit", "free cash flow", "net liquidity", "unit sales",
        "employees", "bev", "xev", "mb.os", "software-defined", "robotaxi",
        "cars ros", "vans ros", "sales share", "g-class", "cla", "glc"
    ],
    "internet_platform": [
        "revenue", "gross profit", "operating", "advertising", "cloud", "ai",
        "games", "fintech", "quarterly", "annual", "users", "growth"
    ],
    "foundation_model_company": [
        "model", "agent", "api", "open platform", "maas", "reasoning",
        "glm", "open source", "research", "annual results", "revenue"
    ],
    "generic_company": [
        "revenue", "profit", "annual", "financial", "product", "service",
        "technology", "market", "growth", "ai"
    ],
}


def score_line(text: str, focus_profile: str) -> int:
    t = normalize_text(text)
    if len(t) < 25:
        return -10
    if is_noise_text(t):
        return -20

    score = 0
    if re.search(r"\d", t):
        score += 2
    if re.search(r"(€|\$|¥|亿元|百万|billion|million|%|YoY|同比|bn)", t, flags=re.I):
        score += 3

    kw = PROFILE_KEYWORDS.get(focus_profile) or PROFILE_KEYWORDS["generic_company"]
    for k in kw:
        if k.lower() in t.lower():
            score += 2

    if len(t) > 220:
        score -= 1
    return score


def extract_evidence(fetch_rows, focus_profile: str):
    items = []
    seen = set()
    for row in fetch_rows:
        body = row.get("body_text") or ""
        title = row.get("title") or row.get("source_name") or "source"
        if not body:
            continue

        lines = []
        for seg in re.split(r"[\n\r]+|(?<=[。！？!?\.])\s+", body):
            one = normalize_text(seg)
            if one:
                lines.append(one)

        scored = []
        for line in lines:
            if line in seen:
                continue
            seen.add(line)
            s = score_line(line, focus_profile)
            if s >= 3:
                scored.append((s, line))

        scored.sort(key=lambda x: (-x[0], -len(x[1])))
        top = [x[1] for x in scored[:8]]

        for idx, line in enumerate(top, 1):
            items.append({
                "source_name": row.get("source_name"),
                "source_type": row.get("source_type"),
                "url": row.get("url"),
                "title": f"{title} / segment {idx:02d}",
                "evidence_type": "body_extract",
                "confidence_score": 0.82 if re.search(r"\d|%|€|\$|亿元|billion|million", line, flags=re.I) else 0.72,
                "text": line,
            })

    items.sort(key=lambda x: (-x["confidence_score"], -len(x["text"])))
    return items[:18]


def extract_metrics(evidence_items):
    metrics = []
    seen = set()
    for item in evidence_items:
        text = item["text"]
        title = item["title"]

        patterns = [
            r'(?i)(revenue[^\.]{0,80}?\b(?:€|\$)?\s?\d+(?:\.\d+)?\s?(?:billion|million|bn|m|亿元|million RMB|billion RMB)?)',
            r'(?i)(ebit[^\.]{0,80}?\b(?:€|\$)?\s?\d+(?:\.\d+)?\s?(?:billion|million|bn|m)?)',
            r'(?i)(free cash flow[^\.]{0,80}?\b(?:€|\$)?\s?\d+(?:\.\d+)?\s?(?:billion|million|bn|m)?)',
            r'(?i)(net liquidity[^\.]{0,80}?\b(?:€|\$)?\s?\d+(?:\.\d+)?\s?(?:billion|million|bn|m)?)',
            r'(?i)(employees?[^\.]{0,50}?\b\d[\d,\.]*)',
            r'(?i)(unit sales[^\.]{0,60}?\b\d+(?:\.\d+)?\s?(?:million|thousand|m|k)?)',
            r'(?i)(?:\+|-)?\d+(?:\.\d+)?%\s*(?:YoY|同比|vs\.)?',
        ]
        for p in patterns:
            for m in re.finditer(p, text):
                one = normalize_text(m.group(0))
                if len(one) < 6:
                    continue
                key = (title, one)
                if key in seen:
                    continue
                seen.add(key)
                metrics.append({
                    "title": title,
                    "metric_text": one,
                })

    return metrics[:16]


def deterministic_sections(target_name, focus_profile, analysis_type, prompt_text, evidence_items, metrics, source_rows):
    executive = []
    if evidence_items:
        executive.extend([x["text"] for x in evidence_items[:3]])
    else:
        executive.append("当前高价值正文证据不足，结论可信度受限。")

    profile_map = {
        "automotive_oem": "收入结构、利润质量、销量与车型结构、软件/智驾/电动化能力、竞争地位与跟踪指标",
        "internet_platform": "收入结构、利润质量、广告/云/游戏等业务结构、AI能力、竞争地位与跟踪指标",
        "foundation_model_company": "模型与平台产品、商业化路径、Agent/推理能力、生态合作、竞争地位与跟踪指标",
        "generic_company": "收入结构、利润质量、产品能力、竞争地位与未来跟踪指标",
    }

    sections = {
        "executive_summary": executive[:4],
        "positioning": [
            f"当前识别的分析类型：{analysis_type}；焦点画像：{focus_profile}。",
            f"结合官方来源与投资者关系材料，重点应看：{profile_map.get(focus_profile, profile_map['generic_company'])}。"
        ],
        "core_evidence": [
            f"{i}. {x['title']}：{x['text']}" for i, x in enumerate(evidence_items[:8], 1)
        ] or ["暂无可用正文证据。"],
        "key_metrics": [
            f"{i}. {x['metric_text']}" for i, x in enumerate(metrics[:10], 1)
        ] or ["当前无高价值结构化指标。"],
        "risks": [
            "当前高价值正文证据不足，部分结论仍需补充财报、业绩会或监管文件验证。",
            "当前版本优先基于官方来源直读结果，若官方页面壳层噪音较重，部分结论仍需人工复核。",
            "对正式高层汇报或投资判断，仍建议继续补充财报、业绩会、监管文件与可比公司数据。"
        ],
        "source_links": [x["url"] for x in source_rows if x.get("url")][:12],
    }
    return sections


def llm_sections(target_name, focus_profile, prompt_text, evidence_items, metrics, source_rows):
    payload = {
        "target_company": target_name,
        "focus_profile": focus_profile,
        "user_prompt": prompt_text,
        "evidence": evidence_items[:12],
        "metrics": metrics[:12],
        "sources": source_rows[:10],
        "requirements": {
            "language": "zh-CN",
            "format": "strict_json",
            "mobile_first": True,
            "no_markdown_fence": True,
            "must_distinguish": ["事实", "推断", "风险"],
            "sections": [
                "executive_summary",
                "positioning",
                "core_evidence",
                "key_metrics",
                "risks",
                "source_links"
            ]
        }
    }
    prompt = (
        "你是企业洞察写作器。基于给定证据，输出严格 JSON。"
        "不要补造没有证据支持的事实。每个 section 输出字符串数组。\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    try:
        resp = call_oris_text(prompt, role="report_generation", timeout_seconds=180)
        if resp.get("ok") and resp.get("text"):
            text = resp["text"].strip()
            m = re.search(r'(\{.*\})', text, flags=re.S)
            if m:
                obj = json.loads(m.group(1))
                for key in ["executive_summary", "positioning", "core_evidence", "key_metrics", "risks", "source_links"]:
                    obj.setdefault(key, [])
                return obj
    except Exception:
        pass
    return None


def render_markdown(target_name, sections):
    out = []
    out.append(f"# {target_name} 公司洞察")
    out.append("")
    out.append("## 一、执行摘要")
    for x in sections.get("executive_summary") or ["暂无"]:
        out.append(f"- {x}")
    out.append("")
    out.append("## 二、公司定位与商业模式")
    for x in sections.get("positioning") or ["暂无"]:
        out.append(f"- {x}")
    out.append("")
    out.append("## 三、核心证据摘录")
    for x in sections.get("core_evidence") or ["暂无"]:
        out.append(f"- {x}")
    out.append("")
    out.append("## 四、指标摘录")
    for x in sections.get("key_metrics") or ["暂无"]:
        out.append(f"- {x}")
    out.append("")
    out.append("## 五、风险与边界")
    for x in sections.get("risks") or ["暂无"]:
        out.append(f"- {x}")
    out.append("")
    out.append("## 六、数据来源链接")
    for x in sections.get("source_links") or []:
        out.append(f"- {x}")
    return "\n".join(out).strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compiled-case-path", default=None)
    ap.add_argument("--prompt-text", default=None)
    args = ap.parse_args()

    if args.compiled_case_path:
        compiled_case_path = Path(args.compiled_case_path)
        if not compiled_case_path.is_absolute():
            compiled_case_path = ROOT / compiled_case_path
        compiled_case = load_json(compiled_case_path)
    elif args.prompt_text:
        r = subprocess.run(
            ["/usr/bin/python3", str(ROOT / "scripts" / "prompt_to_case_compiler_plus_v3.py"), "--prompt-text", args.prompt_text, "--write-output"],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout or "").strip()[:4000])
        compiled_case = json.loads(r.stdout)
        compiled_case_path = ROOT / compiled_case["compiled_case_path"]
    else:
        raise SystemExit("missing compiled case or prompt")

    target = ((compiled_case.get("role_bindings") or {}).get("target_company") or {})
    if not target:
        raise RuntimeError("company_profile direct mode requires detected target_company")

    case_code = compiled_case["case_code"]
    target_name = target.get("display_name") or target.get("name") or "company"
    focus_profile = target.get("focus_profile") or "generic_company"
    prompt_text = compiled_case.get("prompt_text") or args.prompt_text or ""
    analysis_type = compiled_case.get("analysis_type") or "company_profile"

    run_dir = ROOT / "inputs" / "generated_cases" / case_code / ts_compact()
    run_dir.mkdir(parents=True, exist_ok=True)

    source_rows = []
    for src in (target.get("sources") or [])[:8]:
        row = {
            "source_name": src.get("source_name") or src.get("title") or "source",
            "source_type": src.get("source_type") or "official_website",
            "url": src.get("url") or "",
            "official_flag": src.get("official_flag", True),
        }
        fetched = curl_fetch(row["url"]) if row["url"] else {"ok": False, "error": "missing_url", "body_text": "", "title": ""}
        parsed_path = run_dir / f"source_{len(source_rows)+1:02d}_parsed.txt"
        raw_path = run_dir / f"source_{len(source_rows)+1:02d}_raw.json"
        parsed_blob = {
            "title": fetched.get("title") or row["source_name"],
            "url": row["url"],
            "source_type": row["source_type"],
            "publisher": target_name,
            "captured_at": utc_now_iso(),
            "status_code": fetched.get("status_code"),
            "content_type": fetched.get("content_type"),
            "error": fetched.get("error"),
            "body_text": fetched.get("body_text") or "",
        }
        write_json(raw_path, parsed_blob)
        write_text(parsed_path, (fetched.get("body_text") or "").strip())

        source_rows.append({
            **row,
            "fetched_ok": bool(fetched.get("ok")) and bool(fetched.get("body_text")),
            "status_code": fetched.get("status_code"),
            "content_type": fetched.get("content_type"),
            "error": fetched.get("error"),
            "title": fetched.get("title") or row["source_name"],
            "body_text": fetched.get("body_text") or "",
            "raw_storage_path": relpath(raw_path),
            "parsed_text_storage_path": relpath(parsed_path),
        })

    evidence_items = extract_evidence(source_rows, focus_profile)
    metrics = extract_metrics(evidence_items)

    sections = llm_sections(target_name, focus_profile, prompt_text, evidence_items, metrics, source_rows)
    if not sections:
        sections = deterministic_sections(target_name, focus_profile, analysis_type, prompt_text, evidence_items, metrics, source_rows)

    markdown = render_markdown(target_name, sections)
    chat_path = ROOT / "outputs" / "chat_md" / f"{case_code}.md"
    write_text(chat_path, markdown)

    profile_json_path = run_dir / "company_profile_output.json"
    profile_json = {
        "ok": True,
        "mode": "direct_company_profile",
        "schema_version": "v1",
        "ts": utc_now_iso(),
        "request": {
            "prompt_text": prompt_text,
            "company_name": target_name,
            "focus_profile": focus_profile,
        },
        "company": {
            "company_name": target_name,
            "domain": target.get("domain"),
            "region": target.get("region"),
            "focus_profile": focus_profile,
        },
        "sources": [
            {
                "source_name": x["source_name"],
                "source_type": x["source_type"],
                "url": x["url"],
                "official_flag": x["official_flag"],
                "fetched_ok": x["fetched_ok"],
                "status_code": x["status_code"],
                "content_type": x["content_type"],
                "error": x["error"],
                "raw_storage_path": x["raw_storage_path"],
                "parsed_text_storage_path": x["parsed_text_storage_path"],
            }
            for x in source_rows
        ],
        "high_value_evidence_items": evidence_items,
        "derived_metrics": metrics,
        "sections": sections,
        "chat_reply_path": relpath(chat_path),
        "chat_reply_preview": markdown[:4000],
    }
    write_json(profile_json_path, profile_json)

    out = {
        "compiled_case_path": relpath(compiled_case_path),
        "compiler_parser_mode": compiled_case.get("parser_mode"),
        "compiler_execution_mode": compiled_case.get("execution_mode"),
        "compiler_llm_compare_mode": ((compiled_case.get("llm_compare") or {}).get("mode")),
        "compiler_compare_summary": compiled_case.get("compare_summary"),
        "external_skill_candidates": compiled_case.get("external_skill_candidates") or [],
        "evolution_actions": compiled_case.get("evolution_actions") or [],
        "generated_case_paths": {
            "company_profile_output_path": relpath(profile_json_path)
        },
        "official_ingest_summary": {
            "conclusion": "direct_company_profile mode; no DB write in mainline.",
            "core_data": [
                {"field": "entity", "value": target_name},
                {"field": "domain", "value": target.get("domain")},
                {"field": "focus_profile", "value": focus_profile},
                {"field": "source_count", "value": len(source_rows)},
                {"field": "high_value_evidence_count", "value": len(evidence_items)},
                {"field": "derived_metric_count", "value": len(metrics)},
            ],
        },
        "company_profile_output_json": relpath(profile_json_path),
        "company_profile_artifacts": [],
        "evolution_postprocess": {
            "ok": False,
            "reason": "chat_md_direct_mode"
        },
        "registered_files": [],
        "delivery_executor_rc": None,
        "delivery_executor_stdout_tail": "",
        "delivery_executor_stderr_tail": "",
        "chat_delivery_mode": "chat_md",
        "chat_reply_path": relpath(chat_path),
        "chat_reply_preview": markdown[:4000],
        "source_link_count": len([x for x in source_rows if x.get("url")]),
        "registered_count": 0,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
