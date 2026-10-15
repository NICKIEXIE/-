#!/usr/bin/env python3
"""把手册类长文档按章节拆成独立文件，供 skill 按需加载。

为什么要拆：一份 5–10 万字符的手册 ≈ 3–5 万 token，塞进 SKILL.md 正文会让每次加载都爆掉。
拆成章节文件后，正文只给"什么时候读哪个文件"的导航，模型按需读 1–3 个。

支持两种文档风格（自动识别，也可用 --mode 强制）：

  h2       —— 有 Markdown 标题样式（`## 章节名`），如从带样式的 docx 提取的文本
  chapter  —— 没有标题样式，靠编号识别：`第 1 章　` / `附录 A　`（中文全角空格分隔）
              这类文档常见于用 python-docx 直接生成的 docx

用法：
    python split_manual.py <input.md> <output_dir> [--mode auto|h2|chapter]
产出：<output_dir>/NN-<章节名>.md + <output_dir>/_files.tsv（机器可读清单）
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

SAFE = re.compile(r"[^\w\u4e00-\u9fff.\-]+")
CHAPTER_PATTERN = re.compile(r"^(?:第\s*\d+\s*章|附录\s*[A-Za-zＡ-Ｚ])\s*[\u3000\s:：]")
H2_PATTERN = re.compile(r"^##\s+")


def safe_name(title: str, limit: int = 40) -> str:
    cleaned = SAFE.sub("-", title).strip("-")
    return cleaned[:limit].strip("-") or "section"


def detect(lines: list[str], requested: str) -> tuple[str, list[int]]:
    h2 = [index for index, line in enumerate(lines) if H2_PATTERN.match(line)]
    chapter = [index for index, line in enumerate(lines) if CHAPTER_PATTERN.match(line)]
    if requested == "h2":
        return "h2", h2
    if requested == "chapter":
        return "chapter", chapter
    # auto：优先 Markdown 标题；没有则用章编号
    if len(h2) >= 2:
        return "h2", h2
    return "chapter", chapter


def title_of(line: str, mode: str) -> str:
    return line[3:].strip() if mode == "h2" else line.strip()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="按章节拆分长文档")
    parser.add_argument("input", help="输入 Markdown")
    parser.add_argument("output", help="输出目录")
    parser.add_argument("--mode", default="auto", choices=["auto", "h2", "chapter"])
    args = parser.parse_args(argv[1:])

    source = Path(args.input).resolve()
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = source.read_text(encoding="utf-8").splitlines()
    mode, starts = detect(lines, args.mode)
    if not starts:
        print(f"找不到章节标记（mode={mode}）")
        print("  h2 风格需要 `## 标题`；chapter 风格需要 `第 1 章　` 或 `附录 A　`")
        return 1

    total_source = sum(len(line) for line in lines)
    written: list[tuple[str, str, int]] = []
    kept_chars = 0
    order = 0

    preamble = "\n".join(lines[: starts[0]]).strip()
    if preamble:
        order += 1
        name = f"{order:02d}-封面与边界说明.md"
        body = preamble + "\n"
        (out_dir / name).write_text(body, encoding="utf-8")
        written.append((name, "封面与边界说明", len(body)))
        kept_chars += len(body)

    skipped = 0
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        title = title_of(lines[start], mode)
        if title == "目录":
            skipped += 1
            continue
        order += 1
        name = f"{order:02d}-{safe_name(title)}.md"
        body = "\n".join(lines[start:end]).rstrip() + "\n"
        (out_dir / name).write_text(body, encoding="utf-8")
        written.append((name, title, len(body)))
        kept_chars += len(body)

    (out_dir / "_files.tsv").write_text(
        "file\ttitle\tchars\n" + "\n".join(f"{n}\t{t}\t{c}" for n, t, c in written) + "\n",
        encoding="utf-8",
    )

    print(f"源文件      : {source}")
    print(f"识别风格    : {mode}（找到 {len(starts)} 个章节标记）")
    print(f"源文件总字符: {total_source:,}")
    print(f"保留字符数  : {kept_chars:,}（跳过 {skipped} 个目录段）")
    print(f"输出文件数  : {len(written)}  →  {out_dir}")
    print()
    for name, title, chars in written:
        print(f"  {chars:6d}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
