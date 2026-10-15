#!/usr/bin/env python3
"""校验 DSH skill 是否符合加载器的真实契约。

规则镜像自 @deepseek-ai/dsh-skill-filesystem (lib/index.js) 与 @deepseek-ai/dsh-skill
的校验逻辑：

  * SKILL.md 首行必须恰好是 `---`（容忍 CRLF），并以另一行 `---` 闭合
  * frontmatter 必须解析成映射，且只支持单层 `key: value` 标量
  * `name` / `description` 必需且为非空字符串
  * `name` 必须匹配 ^[a-z0-9]+(?:-[a-z0-9]+)*$（kebab-case）
  * `whenToUse` 出现时必须是字符串
  * `disable-model-invocation` / `user-invocable` 接受布尔样式的标量
  * 废弃别名 modelInvocable / userInvocable / disableModelInvocable 会被拒绝
  * `metadata` 可以是映射

加载器对这些问题的处理是**静默忽略**（只在宿主日志留一条 warning），所以这里
一律当成报错，让问题在写的时候就能看见。

用法：
    python validate_skills.py [root ...]        # 默认 <本脚本>/..（套件根 = 发现根）
    python validate_skills.py .dsh/skills
退出码：0 = 全部通过；1 = 存在报错。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:  # 避免 Windows 控制台把中文输出打成乱码
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - 老版本解释器
    pass

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KV_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_-]*):[ \t]*(.*)$")
PATH_REF_RE = re.compile(r"`((?:\.\./)?(?:reference|scripts|templates|assets)/[^`\s]+)`")

DESCRIPTION_MAX = 500
BOOLEAN_KEYS = ("disable-model-invocation", "user-invocable")
KNOWN_KEYS = {"name", "description", "whenToUse", "metadata", *BOOLEAN_KEYS}
LEGACY_KEYS = {
    "modelInvocable": "disable-model-invocation（含义取反）",
    "disableModelInvocation": "disable-model-invocation",
    "userInvocable": "user-invocable",
}
TRUTHY = {"true", "yes", "on", "1"}
FALSY = {"false", "no", "off", "0"}


class FrontmatterError(Exception):
    """frontmatter 结构性错误（加载器会直接跳过该 skill）。"""


def split_frontmatter(text: str) -> tuple[list[str], str]:
    lines = text.splitlines()
    if not lines:
        raise FrontmatterError("文件为空")
    if lines[0] != "---":
        raise FrontmatterError(f"首行必须是恰好 ---，当前是 {lines[0][:40]!r}")
    for index in range(1, len(lines)):
        if lines[index] == "---":
            return lines[1:index], "\n".join(lines[index + 1 :])
    raise FrontmatterError("frontmatter 没有以另一行 --- 闭合")


def parse_scalars(block: list[str]) -> tuple[dict[str, str | None], list[str]]:
    data: dict[str, str | None] = {}
    problems: list[str] = []
    for lineno, raw in enumerate(block, start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0] in (" ", "\t"):
            continue  # 缩进行属于上一个键（例如 metadata 的子项）
        match = KV_RE.match(raw)
        if match is None:
            problems.append(f"第 {lineno} 行不是 key: value 形式：{raw.strip()[:60]!r}")
            continue
        key, value = match.group(1), match.group(2).strip()
        if value == "":
            data[key] = None  # 空值 / 块标量（|、>）—— 后面统一报错
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        data[key] = value
    return data, problems


def check_boolean(value: object, key: str) -> str | None:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in TRUTHY or lowered in FALSY:
            return None
        return f"{key} 必须是布尔值（true/false、1/0、yes/no、on/off），当前是 {value!r}"
    return f"{key} 必须是布尔值，当前是 {value!r}"


def validate_skill(skill_file: Path, is_bundle: bool) -> tuple[list[str], list[str], str]:
    """返回 (errors, warnings, name)。"""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError as error:
        return [f"无法读取：{error}"], [], ""

    try:
        block, body = split_frontmatter(text)
    except FrontmatterError as error:
        return [f"frontmatter 无效：{error} → 该 skill 会被静默忽略"], [], ""

    data, problems = parse_scalars(block)
    errors.extend(problems)

    for key in data:
        if key in LEGACY_KEYS:
            errors.append(
                f"废弃字段 {key!r}：加载器会拒绝整条 skill，请改用 {LEGACY_KEYS[key]!r}"
            )
        elif key not in KNOWN_KEYS:
            warnings.append(f"未知字段 {key!r}：加载器会忽略它")

    name = data.get("name")
    if name is None:
        errors.append("缺少必需的 name")
        name = ""
    elif not isinstance(name, str) or not name:
        errors.append("name 必须是非空字符串（当前是块标量或空值）")
        name = ""
    elif NAME_RE.match(name) is None:
        errors.append(f"name {name!r} 不是 kebab-case（要求 ^[a-z0-9]+(?:-[a-z0-9]+)*$）")

    description = data.get("description")
    if description is None:
        errors.append("缺少必需的 description")
    elif not isinstance(description, str) or not description:
        errors.append("description 必须是非空字符串（当前是块标量或空值）")
    else:
        if len(description) > DESCRIPTION_MAX:
            warnings.append(
                f"description 长 {len(description)} 字符，超过 {DESCRIPTION_MAX}，会被截断"
            )
        if not description.strip():
            errors.append("description 不能只有空白")

    when_to_use = data.get("whenToUse")
    if when_to_use is not None and not isinstance(when_to_use, str):
        errors.append("whenToUse 必须是单行字符串")

    for key in BOOLEAN_KEYS:
        if key in data and data[key] is not None:
            problem = check_boolean(data[key], key)
            if problem:
                errors.append(problem)

    if "metadata" in data:
        metadata = data["metadata"]
        if metadata is None:
            pass  # 缩进子项形式，合法
        else:
            warnings.append("metadata 必须是映射；标量值会被加载器忽略")

    if is_bundle and name and skill_file.parent.name != name:
        warnings.append(
            f"目录名 {skill_file.parent.name!r} 与 name {name!r} 不一致（资源基目录是目录名那条路径）"
        )

    if not body.strip():
        warnings.append("正文为空：模型加载后拿不到任何指令")

    base = skill_file.parent
    for reference in sorted(set(PATH_REF_RE.findall(body))):
        if any(marker in reference for marker in ("<", ">", "*", "…", "N")):
            continue
        if not (base / reference).exists():
            warnings.append(f"正文引用的相对路径不存在：{reference}")

    return errors, warnings, name


# 发现根里这些名字的 .md 是人读文档，不是 skill。
# 加载器其实会扫到它们，然后因为缺 frontmatter 静默忽略——一并识别，避免恒定误报。
IGNORED_ROOT_DOCS = {
    "README", "INSTALL", "LICENSE", "CHANGELOG", "CONTRIBUTING", "SECURITY", "NOTES", "MANIFEST",
}

# 跳过的根级文档，用于在报告里说明（不算错误）
SKIPPED_DOCS: list[Path] = []


def collect_targets(roots: list[Path]) -> list[tuple[Path, bool]]:
    targets: list[tuple[Path, bool]] = []
    for root in roots:
        if root.is_file():
            targets.append((root, False))
            continue
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if entry.is_dir():
                skill_file = entry / "SKILL.md"
                if skill_file.is_file():
                    targets.append((skill_file, True))
            elif entry.suffix == ".md":
                if entry.stem.upper() in IGNORED_ROOT_DOCS and not entry.read_text(
                    encoding="utf-8", errors="replace"
                ).startswith("---"):
                    SKIPPED_DOCS.append(entry)
                    continue
                targets.append((entry, False))
    return targets


def main(argv: list[str]) -> int:
    raw_roots = argv[1:]
    if raw_roots:
        roots = [Path(item).resolve() for item in raw_roots]
    else:
        roots = [Path(__file__).resolve().parent.parent]

    targets = collect_targets(roots)
    if not targets:
        print(f"没有在 {', '.join(str(root) for root in roots)} 下找到任何 skill")
        print("（目录包形如 <根>/<名字>/SKILL.md，平铺形如 <根>/<名字>.md）")
        return 1
    for skipped in SKIPPED_DOCS:
        print(f"[跳过] {skipped.name}（根级人读文档，无 frontmatter，加载器同样会静默忽略）")

    total_errors = 0
    seen: dict[str, list[Path]] = {}

    for skill_file, is_bundle in targets:
        errors, warnings, name = validate_skill(skill_file, is_bundle)
        label = skill_file.parent.name if is_bundle else skill_file.stem
        if errors:
            total_errors += len(errors)
            print(f"[FAIL] {label}  {skill_file}")
        else:
            detail = f"name={name}" if name else ""
            print(f"[ OK ] {label}  {detail}  {skill_file}")
        for message in errors:
            print(f"       错误: {message}")
        for message in warnings:
            print(f"       提示: {message}")
        if name:
            seen.setdefault(name, []).append(skill_file)

    duplicates = {name: paths for name, paths in seen.items() if len(paths) > 1}
    for name, paths in sorted(duplicates.items()):
        total_errors += 1
        print(f"[FAIL] 重名 skill {name!r}：")
        for path in paths:
            print(f"       {path}")
        print("       同名只会有一个生效（发现根 rank 小者胜出）")

    print()
    print(f"共 {len(targets)} 个 skill，{total_errors} 个错误")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
