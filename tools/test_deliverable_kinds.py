#!/usr/bin/env python3
"""交付物脚本的完整性测试：把 8 种 --kind 各跑一遍。

每个 kind 用一份"最小但合法"的 JSON，验证脚本的校验规则与渲染链路都通。
用法：python test_deliverable_kinds.py <套件根目录>
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

META3 = [
    {"label": "客户", "value": "示例客户"},
    {"label": "目标", "value": "示例目标"},
    {"label": "周期", "value": "示例周期"},
]

DOCX_CASES: dict[str, dict] = {
    "plan": {
        "title": "最小起号方案",
        "meta": META3,
        "sections": [
            {"heading": f"章节{i}", "paragraphs": ["正文"]} for i in range(1, 5)
        ],
    },
    "script": {
        "title": "最小脚本表",
        "sections": [
            {
                "heading": "第 1 条：示例选题",
                "table": {
                    "headers": ["段落", "内容", "口播提示"],
                    "rows": [["钩子", "前 3 秒", "高亢"], ["正文", "核心信息", "平稳"], ["结尾", "行动号召", "有力"]],
                },
            }
        ],
    },
    "acceptance": {
        "title": "最小验收单",
        "meta": [{"label": "客户", "value": "A"}, {"label": "服务期", "value": "Q4"}],
        "sections": [
            {
                "heading": "交付物验收",
                "table": {"headers": ["交付物", "数量", "结论"], "rows": [["成片", "60", "通过"]]},
            },
            {"heading": "遗留问题", "bullets": ["无"]},
        ],
    },
    "report": {
        "title": "最小复盘报告",
        "meta": [{"label": "账号", "value": "示例"}],
        "sections": [
            {"heading": "现状", "paragraphs": ["示例"]},
            {"heading": "下一步", "bullets": ["示例动作"]},
        ],
    },
}

XLSX_CASES: dict[str, dict] = {
    "schedule": {"sheets": [{"name": "排期", "headers": ["第几天", "主题"], "rows": [["D1", "自我介绍"]]}]},
    "quote": {"sheets": [{"name": "报价", "headers": ["项目", "金额"], "rows": [["内容生产", 18000]]}]},
    "diagnosis": {"sheets": [{"name": "诊断", "headers": ["问题", "客户回答"], "rows": [["卖什么", "示例"]]}]},
    "metrics": {"sheets": [{"name": "数据", "headers": ["日期", "指标", "数值"], "rows": [["D1", "5秒完播率", 0.32]]}]},
}


def main(argv: list[str]) -> int:
    suite = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parent.parent
    python = sys.executable
    failures = 0

    with tempfile.TemporaryDirectory(prefix="deliverable-kinds-") as workspace:
        work = Path(workspace)
        for kind, spec in DOCX_CASES.items():
            source = work / f"{kind}.json"
            target = work / f"{kind}.docx"
            source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [python, str(suite / "scripts" / "make_docx.py"), "--kind", kind, "--input", str(source), "--output", str(target)],
                capture_output=True, text=True, encoding="utf-8",
            )
            ok = result.returncode == 0 and target.is_file()
            failures += 0 if ok else 1
            print(f"[{'OK  ' if ok else 'FAIL'}] docx/{kind:11s} {result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr.strip()[:120]}")

        for kind, spec in XLSX_CASES.items():
            source = work / f"{kind}.json"
            target = work / f"{kind}.xlsx"
            source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [python, str(suite / "scripts" / "make_xlsx.py"), "--kind", kind, "--input", str(source), "--output", str(target)],
                capture_output=True, text=True, encoding="utf-8",
            )
            ok = result.returncode == 0 and target.is_file()
            failures += 0 if ok else 1
            print(f"[{'OK  ' if ok else 'FAIL'}] xlsx/{kind:11s} {result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr.strip()[:120]}")

    print()
    total = len(DOCX_CASES) + len(XLSX_CASES)
    print(f"{total - failures}/{total} 种 kind 通过")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
