#!/usr/bin/env python3
"""把 skill 套件打成可分发压缩包。

为什么不用 Compress-Archive：Windows PowerShell 的 Compress-Archive 对非 ASCII 文件名
编码处理有历史问题，中文文件名容易在别的机器上变成乱码。Python 的 zipfile 会写入
UTF-8 文件名标志位，跨平台解压正常。

产物：
  <output>.zip          顶层是单一的 <package-name>/ 目录，解压即得干净目录
  包内 MANIFEST.sha256  每个文件的 sha256（sha256sum 格式，便于在目标机器核对完整性）

用法：python package_suite.py <套件根目录> <输出.zip> [--name 包内顶层目录名]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

# 不该进包的东西
EXCLUDE_DIRS = {"__pycache__", ".git", ".idea", ".vscode", "node_modules", ".pytest_cache"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".bak", ".log", ".tmp", ".zip"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def should_skip(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return True
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    if path.name in EXCLUDE_NAMES:
        return True
    return False


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="打包 skill 套件")
    parser.add_argument("suite", help="套件根目录")
    parser.add_argument("output", help="输出 .zip 路径")
    parser.add_argument("--name", default=None, help="包内顶层目录名（默认用包名 dsh-shortvideo-suite）")
    args = parser.parse_args(argv[1:])

    suite = Path(args.suite).resolve()
    output = Path(args.output).resolve()
    top = args.name or "dsh-shortvideo-suite"

    if not suite.is_dir():
        print(f"套件根目录不存在：{suite}")
        return 1
    if not (suite / "README.md").is_file():
        print(f"警告：{suite} 下没有 README.md，确认这是套件根目录？")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    # 1) 暂存一份干净副本（排除 __pycache__ / *.bak 等）
    with tempfile.TemporaryDirectory(prefix="suite-pack-") as workspace:
        staging = Path(workspace) / top
        copied = 0
        for current, dirs, files in os.walk(suite):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            current_path = Path(current)
            relative = current_path.relative_to(suite)
            (staging / relative).mkdir(parents=True, exist_ok=True)
            for name in files:
                source = current_path / name
                if should_skip(relative / name):
                    continue
                shutil.copy2(source, staging / relative / name)
                copied += 1

        # 2) 生成 MANIFEST.sha256
        manifest_lines = []
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                manifest_lines.append(f"{sha256_of(path)}  {path.relative_to(staging).as_posix()}")
        (staging / "MANIFEST.sha256").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

        # 3) 打包
        file_count = 0
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(staging.parent).as_posix())
                    file_count += 1

    # 4) 自检：压缩包能否完整读出
    with zipfile.ZipFile(output) as archive:
        broken = archive.testzip()
        names = archive.namelist()
    if broken is not None:
        print(f"压缩包损坏：{broken}")
        return 1

    size = output.stat().st_size
    print(f"套件根目录 : {suite}")
    print(f"包内顶层   : {top}/")
    print(f"输出       : {output}")
    print(f"文件数     : {file_count}（含 MANIFEST.sha256）")
    print(f"压缩包大小 : {size:,} 字节（{size / 1024:.1f} KB）")
    print(f"zip 自检   : ok（{len(names)} 个条目）")
    print(f"压缩包 sha256: {sha256_of(output)}")
    print()
    print("包内顶层条目：")
    tops = sorted({name.split("/")[1] for name in names if name.count("/") >= 1})
    for item in tops:
        print(f"  {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
