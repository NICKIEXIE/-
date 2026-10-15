#!/usr/bin/env python3
"""把 DOCX 按文档顺序提取成 Markdown，并输出结构统计。

用途：把培训手册一类的知识库文档变成模型可读的文本，同时暴露"纯文本提取会漏掉
什么"（图片、文本框、页眉页脚、批注）。

用法：python extract_docx.py <input.docx> <output.md>
"""

from __future__ import annotations

import sys
import zipfile
from collections import Counter
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

HEADING_PREFIX = {"Heading": "#", "标题": "#"}


def iter_block_items(document: Document):
    """按文档顺序产出 Paragraph / Table。"""
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def heading_level(style_name: str | None) -> int | None:
    if not style_name:
        return None
    if style_name.startswith("Heading"):
        tail = style_name[len("Heading") :].strip()
        if tail.isdigit():
            return int(tail)
    if style_name.startswith("标题"):
        tail = style_name[len("标题") :].strip()
        if tail.isdigit():
            return int(tail)
    return None


def paragraph_markdown(paragraph: Paragraph, stats: Counter) -> str:
    text = paragraph.text.strip()
    style_name = paragraph.style.name if paragraph.style is not None else None
    stats[f"style:{style_name}"] += 1
    if not text:
        return ""
    level = heading_level(style_name)
    if level:
        return f"{'#' * min(level + 1, 6)} {text}"
    if style_name and "List" in style_name:
        return f"- {text}"
    # 带自动编号的段落也当列表处理
    if paragraph._p.pPr is not None and paragraph._p.pPr.numPr is not None:
        return f"- {text}"
    return text


def table_markdown(table: Table, stats: Counter) -> str:
    stats["tables"] += 1
    rows = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            value = " ".join(cell.text.split())
            cells.append(value.replace("|", "\\|"))
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)

    def render(row: list[str]) -> str:
        return "| " + " | ".join(row + [""] * (width - len(row))) + " |"

    lines = [render(rows[0]), "|" + "---|" * width]
    lines.extend(render(row) for row in rows[1:])
    return "\n".join(lines)


def count_package_media(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.startswith("word/media/"):
                counts["media_files"] = counts.get("media_files", 0) + 1
            if name.endswith(".xml") and ("header" in name or "footer" in name):
                counts["header_footer_parts"] = counts.get("header_footer_parts", 0) + 1
            if "comments" in name and name.endswith(".xml"):
                counts["comment_parts"] = counts.get("comment_parts", 0) + 1
    return counts


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    source = Path(argv[1]).resolve()
    target = Path(argv[2]).resolve()
    document = Document(str(source))
    stats: Counter = Counter()

    blocks: list[str] = []
    lines = [f"# {source.stem}", ""]
    properties = document.core_properties
    if properties.title:
        lines.append(f"- 文档标题: {properties.title}")
    if properties.author:
        lines.append(f"- 作者: {properties.author}")
    if properties.last_modified_by:
        lines.append(f"- 最后修改者: {properties.last_modified_by}")
    lines.append("")
    blocks.append("\n".join(lines))

    for block in iter_block_items(document):
        if isinstance(block, Paragraph):
            markdown = paragraph_markdown(block, stats)
        else:
            markdown = table_markdown(block, stats)
        if markdown:
            blocks.append(markdown)

    text = "\n\n".join(blocks) + "\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")

    print(f"源文件    : {source}")
    print(f"输出      : {target}")
    print(f"输出字符数: {len(text):,}")
    print(f"段落数    : {stats.get('style:Normal', 0) + sum(v for k, v in stats.items() if k.startswith('style:') and k != 'style:Normal'):,}")
    print(f"表格数    : {stats['tables']}")
    print(f"内联图片  : {len(document.inline_shapes)}")
    print(f"包内媒体  : {count_package_media(source)}")
    print()
    print("样式分布（前 20）：")
    for name, count in Counter({k.replace("style:", ""): v for k, v in stats.items() if k.startswith("style:")}).most_common(20):
        print(f"  {count:5d}  {name}")
    print()
    print("标题大纲：")
    for match_line in text.splitlines():
        if match_line.startswith("#"):
            print("  " + match_line[:100])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
