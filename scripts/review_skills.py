#!/usr/bin/env python3
"""套件级审查：校验器管不到的契约，在这里查。

`validate_skills.py` 只能检查 frontmatter 语法。本脚本检查的是"内容契约"：

1. description 是否与 `docs/skill-routing.md` 逐字一致（路由正确性的前提）
2. 正文里引用的 `<skill-directory>/../knowledge/…` 是否真实存在（断链 = skill 当场失效）
3. 引用的 `<skill-directory>/../scripts/…` 是否存在
4. 结构骨架是否齐全（定位/交付产物/诊断/工作流/输出模板/失败与回退/自检）
5. 行数与字符数是否在契约区间，结尾是否疑似被截断
6. 每套 skill 特有的红线内容是否出现（agency 不可承诺、team 公开确认vs推演、growth 时效警告、视频号标注…）
7. 是否出现可疑的"编造薛辉原话"句式

用法：python review_skills.py [套件根目录]
退出码：0 = 全部通过；1 = 有需要修的问题。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

REQUIRED_SECTIONS = ["交付产物", "工作流", "失败与回退", "自检"]

# 每套 skill 必须出现的关键内容（子串匹配，任一命中即可）
REQUIRED_CONTENT: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "shortvideo-coach": [
        ("分岔判定（矩阵 vs 精品号）", ("精品号", "单号")),
        ("产能测算", ("产能",)),
        ("轮次问诊", ("第 0 轮", "9 轮", "九轮")),
        ("账号档案落盘", ("账号档案",)),
        ("脚本产出", ("脚本",)),
        ("周复盘", ("复盘",)),
        ("第 8 轮合规红线", ("红线", "合规")),
    ],
    "shortvideo-advisor": [
        ("两种模式（讲师/操刀）", ("讲师模式", "操刀模式")),
        ("角色判定与交接", ("交接", "转入", "交给")),
        ("可信度分级", ("可信度", "【本手册推断】")),
    ],
    "shortvideo-launch": [
        ("视角一的推断标注", ("【本手册推断", "落地建议")),
        ("36 词根缺口说明", ("词根", "缺口")),
        ("诊断 7 项", ("诊断", "变现方式")),
    ],
    "shortvideo-production": [
        ("剪映操作缺口说明", ("剪映", "缺口", "官方教程")),
        ("照读句式", ("照读", "句式")),
        ("表现力三关键点", ("真诚", "情绪", "场景")),
    ],
    "shortvideo-growth": [
        ("时效警告", ("时效", "以官方", "当前数据", "第三方整理")),
        ("5 秒完播率", ("5 秒完播率", "完播率")),
        ("加投停投判据", ("加投", "停投")),
    ],
    "shortvideo-agency": [
        ("不可承诺红线", ("不可承诺", "过程性指标", "效果承诺")),
        ("报价", ("报价",)),
        ("合同风险", ("合同", "风险")),
        ("视角二的推断标注", ("【本手册推断", "落地建议", "非官方")),
    ],
    "shortvideo-team": [
        ("拆片会", ("拆片会",)),
        ("三级流转", ("三级流转", "流转")),
        ("情绪曲线", ("情绪曲线",)),
        ("公开确认与推演区分", ("公开确认", "推演")),
    ],
}

# 视频号必须带的标注（正文里可能写成“非手册内容”或“非本手册内容”）
PLATFORM_MARKS = ("非手册内容", "非本手册内容")

# 制作方署名：必须出现在每个 skill 正文里。
# 用户问“这个 skill 是谁做的”时，上下文里只有被加载的 SKILL.md 正文——
# 目录只有 name+description，README 也不会被自动读取，所以署名必须在正文里。
AUTHOR_MARK = "NICKIE XIE 谢宇翔"

# 可疑的编造句式：把推断说成薛辉原话。
# 注意：这些词大量出现在“否定语境”里（"不是薛辉原话"、"禁止说成薛辉说"），
# 那正是我们要的写法，所以命中后要回头看前文是否是否定词。
FABRICATION_PATTERNS = [
    re.compile(r"薛辉(说|表示|强调|认为)过?[：:，,]?\s*[\"“]"),
    re.compile(r"薛辉原话[：:]"),
]
NEGATIONS = ("不是", "非", "禁止", "不要", "别", "未", "没有", "说成", "所谓", "≠", "不能")

# 正文里的占位引用（如 NN-xxx.md）不是真引用，跳过
PLACEHOLDER_HINTS = ("NN-", "<", ">", "*", "…")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?", text)
    if not match:
        return {}, text
    data: dict[str, str] = {}
    for line in match.group(1).split("\n"):
        kv = re.match(r"^([A-Za-z0-9_-]+):[ \t]*(.*)$", line)
        if kv:
            data[kv[1]] = kv[2].strip()
    return data, text[match.end() :]


def expected_descriptions(routing: Path) -> dict[str, str]:
    r"""从 docs/skill-routing.md 里取出 `## \`name\`` 之后的第一个代码块内容。"""
    text = routing.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for match in re.finditer(r"^## `([a-z0-9-]+)`\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE):
        name, body = match.group(1), match.group(2)
        fence = re.search(r"```[a-z]*\r?\n([\s\S]*?)```", body)
        if fence:
            result[name] = fence.group(1).strip()
    return result


def main(argv: list[str]) -> int:
    suite = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parent.parent
    routing = suite / "docs" / "skill-routing.md"
    # 布局：套件根就是发现根——每个 skill 是根目录下含 SKILL.md 的直接子目录。
    skill_dirs = sorted(
        entry for entry in suite.iterdir() if entry.is_dir() and (entry / "SKILL.md").is_file()
    )
    if not skill_dirs:
        print(f"找不到任何 skill（{suite} 下没有含 SKILL.md 的目录）")
        return 1

    expected = expected_descriptions(routing) if routing.is_file() else {}
    check_descriptions = bool(expected)
    problems: list[str] = []
    print(f"套件：{suite}")
    print(f"路由表：{routing}（解析到 {len(expected)} 条 description）")
    if not check_descriptions:
        print("提示：没有可用的路由表（已安装副本通常不带 docs/），本次跳过 description 逐字比对")
    print()

    for skill_dir in skill_dirs:
        skill_name = skill_dir.name
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            problems.append(f"{skill_name}: 缺少 SKILL.md")
            continue

        text = skill_file.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
        lines = text.splitlines()

        issues: list[str] = []

        # 1) description 逐字一致
        if skill_name in expected:
            actual = frontmatter.get("description", "")
            if actual != expected[skill_name]:
                issues.append(
                    f"description 与路由表不一致（实际 {len(actual)} 字符 / 期望 {len(expected[skill_name])} 字符）"
                )
        elif check_descriptions:
            issues.append("路由表里没有这个 skill 的 description")

        # 2) 行数
        if not 100 <= len(lines) <= 400:
            issues.append(f"行数 {len(lines)} 超出 100–400 区间")

        # 3) 结尾是否疑似截断
        tail = [line for line in lines if line.strip()]
        if tail and not tail[-1].strip().startswith(("-", "#", "|", "1", "2", "3")) and len(tail[-1]) < 8:
            issues.append(f"结尾可疑：{tail[-1][:40]!r}")

        # 4) 结构骨架
        for section in REQUIRED_SECTIONS:
            if f"## {section}" not in body and f"### {section}" not in body and section not in body:
                issues.append(f"缺少结构段落：{section}")

        # 5) 共享资源引用是否存在（跳过 NN-xxx 这类占位）
        #    这三类都是"必须与 skill 目录同级"的共享资源；少装一个就会断链。
        ref_counts: dict[str, int] = {}
        for resource in ("knowledge", "scripts", "templates"):
            refs = set(re.findall(rf"<skill-directory>/\.\./{resource}/([^`\s）」]+)", body))
            ref_counts[resource] = len(refs)
            for ref in sorted(refs):
                if any(hint in ref for hint in PLACEHOLDER_HINTS):
                    continue
                if not (skill_dir / ".." / resource / ref).resolve().exists():
                    issues.append(f"{resource} 引用不存在：{resource}/{ref}")

        # 6) 每套 skill 的红线内容
        for label, needles in REQUIRED_CONTENT.get(skill_name, []):
            if not any(needle in body for needle in needles):
                issues.append(f"缺少必备内容：{label}（期望出现 {' / '.join(needles)} 之一）")

        # 7) 视频号标注：两本手册都不覆盖视频号。
        #    要么带“非本手册内容”标注，要么明确引用建材手册/矩阵调研作为来源。
        cited = "建材矩阵手册" in body or "矩阵/01" in body
        if "视频号" in body and not any(mark in body for mark in PLATFORM_MARKS) and not cited:
            issues.append("提到视频号但没有“非本手册内容”标注，也没有引用建材手册/矩阵调研作为来源")

        # 8) 编造句式（排除否定语境：不是薛辉原话 / 禁止说成薛辉说）
        for pattern in FABRICATION_PATTERNS:
            for hit in pattern.finditer(body):
                window = body[max(0, hit.start() - 14) : hit.start()]
                if any(negation in window for negation in NEGATIONS):
                    continue
                issues.append(f"可疑编造句式：{hit.group(0)[:40]!r}（前文：{window.strip()[-14:]!r}）")

        # 9) 制作方署名（用户问“这个 skill 是谁做的”时，上下文里只有这段正文）
        if AUTHOR_MARK not in body:
            issues.append(f"缺少制作方署名：正文里应出现「{AUTHOR_MARK}」")

        mark = "OK  " if not issues else "FAIL"
        print(f"[{mark}] {skill_name:24s} {len(lines):4d} 行  {len(text):6d} 字符  "
              f"知识 {ref_counts.get('knowledge', 0)}  脚本 {ref_counts.get('scripts', 0)}  模板 {ref_counts.get('templates', 0)}  可信度标记 {len(re.findall(r'【[^】]+】', body))}")
        for issue in issues:
            print(f"         - {issue}")
        problems.extend(f"{skill_name}: {issue}" for issue in issues)

    print()
    if problems:
        print(f"共 {len(problems)} 个问题需要修")
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
