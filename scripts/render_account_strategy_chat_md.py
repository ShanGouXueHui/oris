#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "chat_md"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def safe_list(v):
    return v if isinstance(v, list) else []

def collect_links(obj):
    links = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            s = x.strip()
            if s.startswith("http://") or s.startswith("https://"):
                links.append(s)

    walk(obj)

    out = []
    seen = set()
    for x in links:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def pick_title(compiled_case, account_json):
    for key in ["user_prompt", "prompt_text", "title"]:
        v = compiled_case.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    case_code = (
        compiled_case.get("case_code")
        or account_json.get("case_code")
        or "account_strategy"
    )
    return f"{case_code} 洞察"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account-json-path", required=True)
    ap.add_argument("--compiled-case-path", required=True)
    args = ap.parse_args()

    account_path = Path(args.account_json_path)
    compiled_path = Path(args.compiled_case_path)

    if not account_path.is_absolute():
        account_path = ROOT / account_path
    if not compiled_path.is_absolute():
        compiled_path = ROOT / compiled_path

    account = load_json(account_path)
    compiled = load_json(compiled_path)

    case_code = (
        compiled.get("case_code")
        or account.get("case_code")
        or "account_strategy_case"
    )

    bindings = compiled.get("role_bindings") or {}
    target_partner = (bindings.get("target_partner") or {}).get("name") or "Akkodis"
    cloud_vendor = (bindings.get("cloud_vendor") or {}).get("name") or "Huawei Cloud"
    customers = [
        x.get("name")
        for x in safe_list(bindings.get("customers"))
        if isinstance(x, dict) and x.get("name")
    ]
    competitors = [
        x.get("name")
        for x in safe_list(bindings.get("competitors"))
        if isinstance(x, dict) and x.get("name")
    ]

    links = collect_links(account)

    lines = []
    lines.append(f"# {pick_title(compiled, account)}")
    lines.append("")
    entity_line = f"**涉及主体：** {target_partner} / {cloud_vendor}"
    if customers:
        entity_line += " / " + " / ".join(customers)
    lines.append(entity_line)
    lines.append("")

    lines.append("## 一、执行摘要")
    lines.append(f"- {target_partner} 更像“行业工程交付与客户进入能力”，{cloud_vendor} 更像“AI平台、模型工程、数据闭环与云基础设施能力”，两者联合才有机会打高门槛车企项目。")
    lines.append("- 真正能打动 Top 车企的，不是单点模型，而是行业 know-how、数据闭环、模型训练部署、持续运营、企业级可靠交付的组合。")
    lines.append("- 因此联合方案的核心，不应停留在传统工程服务，而应升级为“工程服务 + AI平台 + 数据治理 + 可持续运营”的组合方案。")
    lines.append("")

    lines.append("## 二、为什么现在值得推进")
    lines.append("- 汽车行业正从单点智能化走向软件定义、数据闭环和模型持续迭代。")
    lines.append("- 车企越来越关注研发提效、测试验证效率、平台复用率、量产交付与后续持续优化能力。")
    lines.append("- 所以谁能把“行业理解 + AI工程化能力”打包成可复制方案，谁就更容易进入高价值客户。")
    lines.append("")

    lines.append("## 三、Akkodis 相对欧洲主要竞对的强弱项")
    lines.append(f"- 重点可比对象：{', '.join(competitors) if competitors else 'Capgemini Engineering、AVL、Alten、Bertrandt'}。")
    lines.append("- 可能强项：工程服务底座、行业客户进入、跨区域交付、顾问式包装能力。")
    lines.append("- 可能短板：若缺少成熟 AI 平台化能力、模型工程标准件、数据闭环抓手，就容易停留在项目制服务。")
    lines.append("- 强竞对通常会在软件定义汽车工具链、测试验证平台、行业方法论沉淀、现成解决方案、全球品牌背书等方面更强。")
    lines.append("")

    lines.append(f"## 四、{cloud_vendor} 最该补给 {target_partner} 的能力")
    lines.append("- 1）AI 开发与训练平台：模型开发、训练、评测、部署一体化。")
    lines.append("- 2）数据治理与闭环：车端 / 测试 / 研发数据的汇聚、清洗、标注、回流。")
    lines.append("- 3）推理与持续运营：让模型交付后还能持续更新，不是一次性项目。")
    lines.append("- 4）企业级安全与可靠交付：满足车企对合规、可审计、稳定性的要求。")
    lines.append(f"- 简单理解：{target_partner} 负责“懂车企、能进场、能交付”，{cloud_vendor} 负责“AI平台、云底座、数据闭环、规模化能力”。")
    lines.append("")

    lines.append("## 五、客户场景拆解")
    if customers:
        for c in customers:
            lines.append(f"### {c}")
            if c == "引望":
                lines.append("- 更适合强调：高阶智驾 / 软件平台 / 能力平台化 / 生态协同。")
                lines.append("- 联合打法：突出工程交付 + AI平台 + 数据闭环 + 模型持续优化，形成更高壁垒的平台型方案。")
            elif c == "北汽":
                lines.append("- 更适合强调：规模化车型导入、研发提效、质量验证、组织级 AI 化升级。")
                lines.append("- 联合打法：突出降本增效、平台复用、项目落地可复制、量产可交付。")
            else:
                lines.append("- 建议围绕研发效率、软件平台、数据闭环、量产交付能力来设计联合方案。")
            lines.append("")
    else:
        lines.append("- 建议按平台型客户、量产型车企、创新型业务单元三类去做差异化打法。")
        lines.append("")

    lines.append("## 六、建议动作")
    lines.append("- 先做 1 个联合 PoC，不要一开始就讲大而全。")
    lines.append("- 先固化 1 份行业模板，再扩成多客户复用方案。")
    lines.append("- 对外口径从“卖能力”改成“卖结果”，例如研发提效、测试缩短、平台复用、模型迭代效率。")
    lines.append("")

    lines.append("## 七、风险提示")
    lines.append("- 当前为手机直读版，不等同于正式汇报版。")
    lines.append("- 若数据时间戳已跨天，应重新洞察，不应长期复用旧结论。")
    lines.append("- 正式售前或高层汇报，仍建议保留 Word / PPT / Excel 证据底表模式。")
    lines.append("")

    lines.append("## 八、数据来源链接")
    for x in links[:30]:
        lines.append(f"- {x}")

    text = "\n".join(lines).strip() + "\n"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{case_code}.md"
    out_path.write_text(text, encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "output_path": str(out_path.relative_to(ROOT)),
        "preview": text[:1200],
        "source_link_count": len(links),
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
