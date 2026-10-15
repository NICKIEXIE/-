#!/usr/bin/env python3
"""把短视频运营 skill 套件安装到 DSH 的 skill 发现根。

安装布局（刻意让正文里的相对路径在**安装后依然可用**）：

    <root>/<skill-name>/SKILL.md          # 7 个 skill
    <root>/knowledge/…                    # 知识库（index.md + 两本手册 + 矩阵 + 问诊清单）
    <root>/scripts/…                      # 校验器、审查器、交付物生成脚本
    <root>/templates/…                    # 账号档案 / 诊断方案 的空模板

于是 skill 正文里的 `<skill-directory>/../knowledge/…`、`../scripts/…`、`../templates/…`
在安装后全部有效。**这三者必须与 skill 目录同级——少装一个，对应引用就断链。**

用法：
    python install.py                     # 装到 $DSH_HOME/skills
    python install.py --root <目录>
    python install.py --dry-run
    python install.py --force             # 覆盖已存在的同名目录
    python install.py --with-docs         # 连 docs/（人读的规格）一起装
退出码：0 = 安装完成且校验通过。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

# 与 skill 目录同级、必须一起安装的共享资源（键=源目录名，值=说明）
SHARED_DIRS = {
    "knowledge": "知识库",
    "scripts": "共享脚本",
    "templates": "模板",
}


def default_root() -> Path:
    dsh_home = os.environ.get("DSH_HOME")
    base = Path(dsh_home) if dsh_home else Path.home() / ".dsh"
    return base / "skills"


def within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def replace_dir(source: Path, target: Path, root: Path, label: str) -> bool:
    """整目录替换（避免残留旧文件）。返回是否执行。"""
    if not source.is_dir():
        print(f"警告：缺少 {label} 源目录 {source}（skill 正文引用它时会断链）")
        return False
    if target.exists() and not target.is_symlink():
        if not within(target, root) or target == root:
            print(f"拒绝删除目标根之外的路径：{target}")
            return False
        shutil.rmtree(target)
    elif target.is_symlink():
        target.unlink()
    shutil.copytree(source, target)
    print(f"已安装{label}：{target}")
    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="安装短视频运营 skill 套件")
    parser.add_argument("--root", default=None, help="目标发现根（默认 $DSH_HOME/skills）")
    parser.add_argument("--suite", default=None, help="套件根目录（默认本脚本的上一级）")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的同名目录")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划")
    parser.add_argument("--with-docs", action="store_true", help="连 docs/ 一起装（人读的规格，运行时不需要）")
    args = parser.parse_args(argv[1:])

    suite = Path(args.suite).resolve() if args.suite else Path(__file__).resolve().parent.parent
    # 布局：套件根就是发现根 —— 每个 skill 是根目录下含 SKILL.md 的直接子目录
    skill_dirs = sorted(
        entry for entry in suite.iterdir() if entry.is_dir() and (entry / "SKILL.md").is_file()
    )
    if not skill_dirs:
        print(f"{suite} 下没有任何 skill 目录（判定标准：目录里有 SKILL.md）")
        return 1

    root = Path(args.root).expanduser().resolve() if args.root else default_root().resolve()
    print(f"套件根目录 : {suite}")
    print(f"目标发现根 : {root}")
    print(f"待装 skill : {len(skill_dirs)} 个（{'、'.join(d.name for d in skill_dirs)}）")
    print()

    planned: list[tuple[Path, Path]] = []
    for skill_dir in skill_dirs:
        target = root / skill_dir.name
        if target.exists() and not args.force:
            print(f"跳过（已存在，用 --force 覆盖）：{target}")
            continue
        planned.append((skill_dir, target))

    if args.dry_run:
        for source, target in planned:
            print(f"[dry-run] 复制 {source} -> {target}")
        for name, label in SHARED_DIRS.items():
            source = suite / name
            if source.is_dir():
                print(f"[dry-run] 复制 {source} -> {root / name}   （{label}）")
            else:
                print(f"[dry-run] 警告：缺少 {source}（{label}）")
        if args.with_docs and (suite / "docs").is_dir():
            print(f"[dry-run] 复制 {suite / 'docs'} -> {root / 'docs'}")
        return 0

    root.mkdir(parents=True, exist_ok=True)

    # 1) skill 目录
    for source, target in planned:
        if target.exists():
            if not within(target, root) or target == root:
                print(f"拒绝删除目标根之外的路径：{target}")
                return 1
            shutil.rmtree(target)
        shutil.copytree(source, target)
        print(f"已安装 skill：{target / 'SKILL.md'}")

    # 2) 与 skill 目录同级的共享资源 —— 少装任何一个，skill 正文的引用就会断链
    missing: list[str] = []
    for name, label in SHARED_DIRS.items():
        if not replace_dir(suite / name, root / name, root, label):
            missing.append(name)

    # 3) 可选：人读的规格文档
    if args.with_docs:
        replace_dir(suite / "docs", root / "docs", root, "文档")

    # 4) 自检
    validator = root / "scripts" / "validate_skills.py"
    if validator.is_file():
        print()
        print("校验已安装内容：")
        result = subprocess.run([sys.executable, str(validator), str(root)], check=False)
        if result.returncode != 0:
            print("校验未通过")
            return 1

    reviewer = root / "scripts" / "review_skills.py"
    if reviewer.is_file():
        print()
        print("内容契约检查（引用是否断链、结构是否完整）：")
        result = subprocess.run([sys.executable, str(reviewer), str(root)], check=False)
        if result.returncode != 0:
            print("内容契约检查未通过")
            return 1

    print()
    if missing:
        print(f"安装完成，但缺少共享目录：{'、'.join(missing)} —— skill 正文里对它们的引用会断链")
        return 1
    print("完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
