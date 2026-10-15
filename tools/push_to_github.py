#!/usr/bin/env python3
"""把套件目录推送到 GitHub —— 不需要安装 git，只用 GitHub REST API（标准库 urllib）。

为什么不用 git：目标机器可能没有 git、也没有 SSH 密钥，而且交互式登录在这个环境里做不了。
Git Data API 可以用 4 次请求把一个目录变成一次 commit（文本文件直接内联进 tree）。

用法：
    python push_to_github.py --source <目录> --owner <用户名或组织> --repo <仓库名> ^
        [--token-file <文件>] [--branch main] [--message "..."] [--public] [--dry-run] [--replace]

令牌读取顺序：--token-file → 环境变量 GITHUB_TOKEN → GH_TOKEN

安全约定：
  * 任何输出都不打印令牌；
  * 出错信息里把令牌替换成 ***；
  * 默认只做增量（以远端当前树为 base_tree），不会删除远端已有文件；--replace 才整树替换。
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

API = "https://api.github.com"
EXCLUDE_DIRS = {"__pycache__", ".git", ".idea", ".vscode", "node_modules", ".pytest_cache"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".bak", ".log", ".tmp", ".zip"}


class PushError(Exception):
    pass


def redact(text: str, token: str | None) -> str:
    if token:
        text = text.replace(token, "***")
    return text


def request(method: str, path: str, token: str, body: dict | None = None, allow_404: bool = False):
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "shortvideo-suite-publisher")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:400]
        if allow_404 and error.code == 404:
            return None
        raise PushError(f"{method} {path} → HTTP {error.code}: {redact(detail, token)}") from None
    except urllib.error.URLError as error:
        raise PushError(f"{method} {path} → 网络错误: {redact(str(error.reason), token)}") from None


def collect_files(source: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for current, dirs, names in os.walk(source):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        current_path = Path(current)
        for name in names:
            path = current_path / name
            if path.suffix.lower() in EXCLUDE_SUFFIXES:
                continue
            relative = path.relative_to(source).as_posix()
            files.append((relative, path))
    return sorted(files)


def read_token(args) -> str:
    if args.token_file:
        path = Path(args.token_file).expanduser()
        if not path.is_file():
            raise PushError(f"令牌文件不存在：{path}")
        token = path.read_text(encoding="utf-8").strip()
        if not token:
            raise PushError(f"令牌文件是空的：{path}")
        return token
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    raise PushError(
        "没有找到令牌。请用 --token-file <文件> 指定，或设置环境变量 GITHUB_TOKEN。\n"
        "  （不要把令牌贴在对话里——写在文件里更安全）"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="把目录推送到 GitHub（无需 git）")
    parser.add_argument("--source", required=True, help="要上传的本地目录")
    parser.add_argument("--owner", required=True, help="GitHub 用户名或组织名")
    parser.add_argument("--repo", required=True, help="仓库名")
    parser.add_argument("--token-file", default=None, help="令牌文件路径（优先级最高）")
    parser.add_argument("--branch", default=None, help="分支名（默认用仓库的 default_branch）")
    parser.add_argument("--message", default=None, help="提交信息")
    parser.add_argument("--public", action="store_true", help="建为公开仓库（默认私有）")
    parser.add_argument("--create", action="store_true", help="仓库不存在时尝试创建（需要令牌有建仓权限）")
    parser.add_argument("--replace", action="store_true", help="整树替换（会删除远端多余文件）")
    parser.add_argument("--dry-run", action="store_true", help="只列出将要上传的文件，不写远端")
    args = parser.parse_args(argv[1:])

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"源目录不存在：{source}")
        return 1

    files = collect_files(source)
    if not files:
        print(f"{source} 下没有可上传的文件")
        return 1

    total_bytes = sum(path.stat().st_size for _, path in files)
    print(f"源目录   : {source}")
    print(f"目标仓库 : {args.owner}/{args.repo}（{'公开' if args.public else '私有'}）")
    print(f"文件数   : {len(files)}（合计 {total_bytes / 1024:.1f} KB）")
    if args.dry_run:
        print()
        for relative, path in files:
            print(f"  {path.stat().st_size:8d}  {relative}")
        print()
        print("[dry-run] 未写入远端")
        return 0

    try:
        token = read_token(args)
    except PushError as error:
        print(error)
        return 2

    try:
        account = request("GET", "/user", token)
        print(f"令牌身份 : {account.get('login')}")

        repo = request("GET", f"/repos/{args.owner}/{args.repo}", token, allow_404=True)
        if repo is None:
            if not args.create:
                print(
                    f"\n远端仓库 {args.owner}/{args.repo} 不存在。\n"
                    "最省事也最安全：请先在网页上建一个**空仓库**（不要勾选 README / .gitignore / license），"
                    "然后重新运行本命令；这样令牌只需要该仓库的 Contents 读写权限。\n"
                    "或者加 --create（要求令牌具备建仓权限）。"
                )
                return 2
            repo = request(
                "POST",
                "/user/repos" if args.owner == account.get("login") else f"/orgs/{args.owner}/repos",
                token,
                {
                    "name": args.repo,
                    "private": not args.public,
                    "description": "Short-video operations skill suite (DeepSeek Harness)",
                    "auto_init": False,
                },
            )
            print(f"已创建仓库 : {repo['html_url']}")

        branch = args.branch or repo.get("default_branch") or "main"
        ref = request("GET", f"/repos/{args.owner}/{args.repo}/git/ref/heads/{branch}", token, allow_404=True)
        parent_sha = ref["object"]["sha"] if ref else None
        base_tree = None
        if parent_sha:
            parent = request("GET", f"/repos/{args.owner}/{args.repo}/git/commits/{parent_sha}", token)
            base_tree = parent["tree"]["sha"]
            print(f"现有分支   : {branch} @ {parent_sha[:8]}（增量更新）")
        else:
            print(f"远端分支   : {branch} 尚不存在（首次推送）")

        tree_entries = []
        binary_count = 0
        for index, (relative, path) in enumerate(files, start=1):
            raw = path.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                binary_count += 1
                blob = request(
                    "POST", f"/repos/{args.owner}/{args.repo}/git/blobs", token,
                    {"content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"},
                )
                tree_entries.append({"path": relative, "mode": "100644", "type": "blob", "sha": blob["sha"]})
            else:
                tree_entries.append(
                    {"path": relative, "mode": "100644", "type": "blob", "content": text.replace("\r\n", "\n")}
                )
            if index % 25 == 0:
                print(f"  已准备 {index}/{len(files)} 个文件…")

        tree_body: dict = {"tree": tree_entries}
        if base_tree and not args.replace:
            tree_body["base_tree"] = base_tree
        tree = request("POST", f"/repos/{args.owner}/{args.repo}/git/trees", token, tree_body)

        message = args.message or f"Publish shortvideo-suite ({len(files)} files)"
        commit_body: dict = {"message": message, "tree": tree["sha"]}
        if parent_sha and not args.replace:
            commit_body["parents"] = [parent_sha]
        commit = request("POST", f"/repos/{args.owner}/{args.repo}/git/commits", token, commit_body)

        if parent_sha:
            request("PATCH", f"/repos/{args.owner}/{args.repo}/git/refs/heads/{branch}", token, {"sha": commit["sha"], "force": False})
        else:
            request("POST", f"/repos/{args.owner}/{args.repo}/git/refs", token,
                    {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})

        print()
        print(f"完成：{len(files)} 个文件（含二进制 {binary_count} 个）→ {args.owner}/{args.repo}@{branch}")
        print(f"提交  ：{commit['sha'][:8]}  {message}")
        print(f"地址  ：{repo['html_url']}")
        if not args.public:
            print("提示  ：这是私有仓库；要给别人看，去 Settings → Collaborators 邀请，或改可见性。")
        return 0
    except PushError as error:
        print(f"\n失败：{error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
