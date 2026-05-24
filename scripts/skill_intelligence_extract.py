#!/usr/bin/env python3
"""Extract read-only skill intelligence from quarantined candidate indexes.

This script does not install or execute third-party skills. It parses markdown
indexes cloned under vendor/skill_candidates/ and produces a shortlist of skill
names/links/categories that may be useful for ORIS.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ORIS_DIR = Path("/home/admin/projects/oris")
QUARANTINE_DIR = ORIS_DIR / "vendor" / "skill_candidates"
OUT_DIR = ORIS_DIR / "logs" / "dev_employee" / "skill_audit"
OUT_JSON = OUT_DIR / "skill_intelligence_20260525.json"
OUT_MD = OUT_DIR / "skill_intelligence_20260525.md"

LINK_RE = re.compile(r"^-\s+\[(?P<name>[^\]]+)\]\((?P<url>[^)]+)\)\s*-\s*(?P<desc>.*)$")
HEADING_RE = re.compile(r"^#{1,4}\s+(?P<title>.+?)\s*$")
DETAILS_RE = re.compile(r"<summary>.*?(?P<title>[A-Za-z0-9 &/+-]+).*?</summary>", re.I)

PRIORITY_PATTERNS = {
    "github_dev_workflow": re.compile(r"\b(git|github|pull request|issue|commit|repository|repo|branch|code review)\b", re.I),
    "coding_agent": re.compile(r"\b(coding agent|ide|python|fastapi|pytest|test|lint|debug|refactor|codebase)\b", re.I),
    "docs_markdown": re.compile(r"\b(markdown|docs?|documentation|readme|pdf|document|summari[sz]e|report)\b", re.I),
    "research_search": re.compile(r"\b(search|research|web fetch|browserless|crawler|arxiv|semantic scholar|crossref)\b", re.I),
    "devops_cloud": re.compile(r"\b(devops|docker|kubernetes|k8s|ci|cd|deploy|cloud|server|logs?)\b", re.I),
}

BLOCK_PATTERNS = {
    "credential_or_secret": re.compile(r"\b(password|credential|secret|token|api key|1password|bitwarden|dashlane|vault|otp)\b", re.I),
    "browser_or_scraping": re.compile(r"\b(browser|playwright|puppeteer|selenium|chrome|captcha|anti-detection|scrap(e|ing))\b", re.I),
    "crypto_finance": re.compile(r"\b(crypto|wallet|defi|blockchain|trading|trade|token price|usdc|bitcoin|ethereum)\b", re.I),
    "social_posting": re.compile(r"\b(twitter|x \(|instagram|tiktok|facebook|linkedin|post social|social media)\b", re.I),
    "email_calendar": re.compile(r"\b(gmail|email|calendar|m365|outlook)\b", re.I),
}

MAX_ITEMS_PER_FILE = 2000


@dataclass
class SkillItem:
    source_repo_dir: str
    source_file: str
    category: str
    name: str
    url: str
    description: str
    priority_tags: list[str]
    block_tags: list[str]
    recommendation: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def iter_markdown_files(root: Path) -> Iterable[Path]:
    for repo_dir in sorted(root.iterdir() if root.exists() else []):
        if not repo_dir.is_dir():
            continue
        for path in repo_dir.rglob("*.md"):
            if ".git" in path.parts:
                continue
            yield path


def classify(text: str) -> tuple[list[str], list[str], str]:
    priority = [name for name, pattern in PRIORITY_PATTERNS.items() if pattern.search(text)]
    blocked = [name for name, pattern in BLOCK_PATTERNS.items() if pattern.search(text)]
    if blocked:
        recommendation = "reject_for_oris_runtime"
    elif priority:
        recommendation = "review_candidate_read_only"
    else:
        recommendation = "low_priority_intelligence_only"
    return priority, blocked, recommendation


def extract_from_file(path: Path) -> list[SkillItem]:
    rel_parts = path.relative_to(QUARANTINE_DIR).parts
    repo_dir = rel_parts[0] if rel_parts else "unknown"
    rel_file = "/".join(rel_parts[1:]) if len(rel_parts) > 1 else path.name
    items: list[SkillItem] = []
    category = path.stem.replace("-", " ").title()

    text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        heading = HEADING_RE.match(line.strip())
        if heading:
            category = heading.group("title").strip().replace("#", "")
            continue
        details = DETAILS_RE.search(line)
        if details:
            category = details.group("title").strip()
            continue
        match = LINK_RE.match(line.strip())
        if not match:
            continue
        name = match.group("name").strip()
        url = match.group("url").strip()
        desc = match.group("desc").strip()
        if not url.startswith(("http://", "https://")):
            continue
        combined = f"{category} {name} {desc} {url}"
        priority, blocked, recommendation = classify(combined)
        items.append(
            SkillItem(
                source_repo_dir=repo_dir,
                source_file=rel_file,
                category=category,
                name=name,
                url=url,
                description=desc[:500],
                priority_tags=priority,
                block_tags=blocked,
                recommendation=recommendation,
            )
        )
        if len(items) >= MAX_ITEMS_PER_FILE:
            break
    return items


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_items: list[SkillItem] = []
    for md in iter_markdown_files(QUARANTINE_DIR):
        all_items.extend(extract_from_file(md))

    reviewable = [item for item in all_items if item.recommendation == "review_candidate_read_only"]
    rejected = [item for item in all_items if item.recommendation == "reject_for_oris_runtime"]
    low = [item for item in all_items if item.recommendation == "low_priority_intelligence_only"]

    tag_counts: dict[str, int] = {}
    for item in all_items:
        for tag in item.priority_tags + item.block_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    def item_dict(item: SkillItem) -> dict[str, object]:
        return {
            "source_repo_dir": item.source_repo_dir,
            "source_file": item.source_file,
            "category": item.category,
            "name": item.name,
            "url": item.url,
            "description": item.description,
            "priority_tags": item.priority_tags,
            "block_tags": item.block_tags,
            "recommendation": item.recommendation,
        }

    payload = {
        "generated_at": now_iso(),
        "policy": "read_only_intelligence_extraction_no_install_no_execution",
        "source_quarantine_dir": str(QUARANTINE_DIR),
        "counts": {
            "total_items": len(all_items),
            "review_candidate_read_only": len(reviewable),
            "reject_for_oris_runtime": len(rejected),
            "low_priority_intelligence_only": len(low),
        },
        "tag_counts": dict(sorted(tag_counts.items())),
        "reviewable_top": [item_dict(item) for item in reviewable[:120]],
        "rejected_sample": [item_dict(item) for item in rejected[:120]],
        "low_priority_sample": [item_dict(item) for item in low[:80]],
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Skill Intelligence Extraction — 2026-05-25",
        "",
        "Policy: read-only intelligence extraction only. No skill was installed or executed.",
        "",
        "## Counts",
        "",
        f"- Total items parsed: `{len(all_items)}`",
        f"- Reviewable read-only candidates: `{len(reviewable)}`",
        f"- Rejected for ORIS runtime: `{len(rejected)}`",
        f"- Low priority intelligence only: `{len(low)}`",
        "",
        "## Priority tag counts",
        "",
    ]
    for tag, count in sorted(tag_counts.items(), key=lambda pair: (-pair[1], pair[0])):
        lines.append(f"- `{tag}`: {count}")

    lines.extend(["", "## Top reviewable candidates", "", "| Name | Tags | Source | Description |", "|---|---|---|---|"])
    for item in reviewable[:50]:
        tags = ", ".join(item.priority_tags)
        desc = item.description.replace("|", " ")[:220]
        lines.append(f"| [{item.name}]({item.url}) | `{tags}` | `{item.source_repo_dir}/{item.source_file}` | {desc} |")

    lines.extend(["", "## Runtime rejection categories", ""])
    for item in rejected[:40]:
        tags = ", ".join(item.block_tags)
        lines.append(f"- `{item.name}` — block tags `{tags}` — source `{item.source_repo_dir}/{item.source_file}`")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"INTELLIGENCE_JSON={OUT_JSON}")
    print(f"INTELLIGENCE_MD={OUT_MD}")
    print(json.dumps(payload["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
