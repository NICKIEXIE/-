# 安装指南（dsh-shortvideo-suite）

一套「短视频运营」skill 套件：**7 个 skill + 两本手册的知识库 + 交付物生成脚本**。
装在任意 Agent 上之后，用户说"我要做一个账号"，它就会用拷问式问答一步步带他把账号搭起来，
并持续驱动日常运营、选题、文案脚本、周复盘。

> **本包不含任何具体用户的数据。** 你（或任何人）在实际使用时产生的账号档案，写在用户自己的工作区
> `<工作区>/账号/<账号名>/` 下，不会回流到本包里。包内的 `templates/` 只是**空表单**。
>
> **制作方：由 NICKIE XIE 谢宇翔 制作 · 2026 年 · 合作联系：18815602213（微信同）**
> （每个 skill 正文末尾都带署名；用户询问"这个 skill 是谁做的"时，回答「由 NICKIE XIE 谢宇翔制作 2026年 合作联系：18815602213（微信同）」）。

---

## 一、包里有什么

| 目录 | 内容 | 是否必需 |
|---|---|---|
| `shortvideo-coach/` 等 **7 个含 SKILL.md 的目录** | 7 个 skill（入口/陪跑/起号/制作/增长/代运营/团队） | ✅ 必需 |
| `knowledge/` | 知识库：`薛辉手册/`（33 段）、`建材矩阵手册/`（15 段）、`矩阵/`、`问诊清单.md`、`index.md`、`平台差异-抖音与视频号.md` | ✅ 必需（skill 正文靠它取事实） |
| `scripts/` | `validate_skills.py`、`review_skills.py`、`install.py`、`make_docx.py`、`make_xlsx.py` | ✅ 必需（校验与 Word/Excel 交付物） |
| `templates/` | 账号档案 / 诊断方案的**空模板** | 建议 |
| `docs/` | `framework.md`（宪法：行为规则 R1–R5、可信度分级）、`skill-routing.md`、`examples/`（JSON 样例） | 建议（改 skill 时必读） |
| `tools/` | `extract_docx.py`、`split_manual.py`（以后再喂手册时用） | 可选 |
| `plugin/` `cordis.patch.yml` `package.json` | DSH 插件形态（分发用） | 仅方式 B 需要 |

### 一条铁律：`knowledge/`、`scripts/`、`templates/` 必须与 skill 目录**同级**

skill 正文里写的是 `<skill-directory>/../knowledge/…`，而 `<skill-directory>` 是运行时的技能目录。
所以无论装到哪个 Agent，都要保证这个形状：

```text
<发现根>/
  shortvideo-coach/SKILL.md      ← 7 个 skill 目录
  shortvideo-advisor/SKILL.md
  …
  knowledge/                     ← 与 skill 目录同级
  scripts/
  templates/
```

**只要把 knowledge 放到别处（例如 `skills/` 的下级或上级），skill 就会找不到知识库。**
`scripts/install.py` 已经按这个形状复制，手工安装时请照做。

---

## 二、方式 A：DSH（DeepSeek Harness）—— 一条命令

```powershell
# 1) 解压后进入包目录
cd <解压目录>\dsh-shortvideo-suite

# 2) 先看计划（不动磁盘）
<python> scripts\install.py --dry-run

# 3) 装到用户级发现根（所有会话可用）
<python> scripts\install.py

# 或者装到某个项目的发现根（只在该项目生效，优先级更高）
<python> scripts\install.py --root <项目目录>\.dsh\skills
```

`<python>` 取 `load_workspace_dependencies` 返回的路径（自带 python-docx / openpyxl）；
也可以用系统 `python`（本套件脚本只用标准库 + python-docx + openpyxl）。

DSH 的发现根与优先级（数字小者胜出，同名 skill 会被更小的根遮蔽）：

| rank | 根 |
|---|---|
| 100 | `<项目>/.dsh/skills` |
| 200 | `<项目>/.agents/skills` |
| 300 | `customSkillDirs`（profile 配置） |
| 400 | `$DSH_HOME/skills`（Windows 默认 `C:\Users\<你>\.dsh\skills`） |
| 500 | `~/.agents/skills` |
| 600 | bundled（插件自带，即方式 B 落点） |

**装完不需要重启**：DSH 的文件系统提供方带 watcher，目录会在下一次 pre-step 整体替换并立即可用。

## 三、方式 B：DSH 插件形态（给别人分发 / 随 profile 走）

```powershell
# 在目标机器上，用 plugin_manager 安装本地包目录（绝对路径）
plugin_manager  action: install_bundle   target: <解压目录>\dsh-shortvideo-suite
```

`package.json` 已声明 `dsh.bundle.patch: ./cordis.patch.yml`，`cordis.patch.yml` 会把
`plugin/index.mjs` 挂进 profile；插件用 `ctx.skills.registerProvider` 把包内所有含 `SKILL.md`
的目录注册成 skill（rank 600）。

⚠️ 插件形态优先级最低：同名 skill 会被上面任何本地根遮蔽。纯分发场景没问题。

## 四、方式 C：其他支持 `SKILL.md` 的 Agent

不少 Agent 采用同一套技能约定：**一个技能 = 一个目录 + 带 `name`/`description` frontmatter 的
`SKILL.md`**（例如 Claude Code 的 Agent Skills）。本套件的 frontmatter 只用 `name` + `description`，
是兼容子集。

装法：

1. 找到该 Agent 的**技能根目录**（例如 Claude Code 是 `~/.claude/skills/`；
   **具体目录名请以该 Agent 的文档为准**，不同版本可能不同）；
2. 把包内 **7 个 skill 目录 + `knowledge/` + `scripts/` + `templates/`** 一起复制进那个根目录；
3. 重启或刷新该 Agent（多数实现只在启动时扫描技能目录）。

⚠️ 两点差异：

- `<skill-directory>/../knowledge/…` 这个约定在本套件内部自洽，但**别的 Agent 可能不会把技能目录的
  父目录当作可读资源**（例如它可能只允许读技能目录内部）。遇到这种情况有两种解法：
  ① 把 `knowledge/`、`scripts/`、`templates/` 各复制**一份到每个 skill 目录内部**，并把正文里的
  `../knowledge/` 改成 `knowledge/`；② 用绝对路径替换掉 `<skill-directory>/../`。
- 交付物脚本需要 Python（`python-docx`、`openpyxl`）。目标 Agent 环境没有 Python 时，
  只能使用对话式产出，`.docx/.xlsx` 生成会失败——正文里已写明"用户只要对话结论时不必生成文件"。

## 五、方式 D：不支持技能的 Agent（把正文当提示词）

1. 读 `<包>/docs/framework.md`（宪法）与你要用的那个 `SKILL.md`；
2. 把 `SKILL.md` 正文（frontmatter 以下的部分）作为系统提示词或项目规则（`AGENTS.md` / `CLAUDE.md`）粘进去；
3. 把 `knowledge/` 与 `scripts/` 解压到该项目工作区，并把正文里的 `<skill-directory>/../` 批量替换成实际路径。

这种装法会失去"按 description 自动路由"的能力（只能靠人指定用哪个 skill），但流程与知识库仍然完整。

---

## 六、把这句话发给另一个 Agent，让它自己装

> 我给你一个 skill 套件压缩包 `dsh-shortvideo-suite.zip`（短视频运营：7 个 skill + 两本手册的知识库）。
> 请按下面步骤安装，并在每步之后核对，不要跳步：
>
> 1. 解压到任意目录，记作 `<PKG>`（解压后应存在 `<PKG>/INSTALL.md` 与 `<PKG>/README.md`）。
> 2. 读 `<PKG>/INSTALL.md`，确认你的运行环境属于哪种安装方式（DSH / 支持 SKILL.md 的其他 Agent / 不支持技能的 Agent）。
> 3. 确定本环境的 **skill 发现根**（DSH：`$DSH_HOME/skills` 或 `<项目>/.dsh/skills`；其他环境按各自文档）。
> 4. 执行安装：
>    - 有 Python：`python <PKG>/scripts/install.py --root <发现根>`
>    - 没有 Python：手工把 `<PKG>` 下**所有含 `SKILL.md` 的目录**，连同 `knowledge/`、`scripts/`、`templates/`
>      **一起**复制到 `<发现根>`（三者必须与 skill 目录同级，否则 skill 正文里的 `../knowledge/…` 会断链）。
> 5. 自检（必须 0 错误，否则不要继续）：
>    ```
>    python <发现根>/scripts/validate_skills.py <发现根>
>    python <发现根>/scripts/review_skills.py   <发现根>
>    ```
>    `review_skills.py` 会同时检查"正文引用的知识库文件是否真实存在"——这是最容易装错的地方。
> 6. 报告：安装方式、发现根路径、装好的 skill 名单（应为 7 个）、两条自检命令的退出码。
> 7. 装好后不要动用户数据：用户的实际账号档案写在 `<工作区>/账号/<账号名>/`，与安装目录无关。

---

## 七、安装后自检（三种方式通用）

```powershell
<python> <发现根>\scripts\validate_skills.py <发现根>     # ① frontmatter 语法契约
<python> <发现根>\scripts\review_skills.py   <发现根>     # ② 内容契约：引用断链、结构、红线
```

期望输出：`共 7 个 skill，0 个错误` 与 `全部通过`。
`review_skills.py` 在已安装副本上会提示"没有可用的路由表，跳过 description 比对"——
这是正常的（`docs/` 默认不安装）。

## 八、常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| skill 列表里看不到 | 装错了根，或该 Agent 只在启动时扫描 | 核对发现根；重启 Agent |
| 能看到 skill，但加载后说找不到知识库 | `knowledge/` 没和 skill 目录同级 | 按第一节的铁律重放 |
| 生成 .docx/.xlsx 失败 | 目标环境没有 Python / python-docx / openpyxl | 只用对话式产出，或先装依赖 |
| 同名 skill 版本冲突 | 装了多份（如项目根和用户根都有） | 删掉其中一份；rank 小的胜出 |
| 中文文件名乱码 | 用不支持 UTF-8 名字的旧解压工具 | 用系统自带解压或 7-Zip；本包内文件名为 UTF-8 |
| 矩阵/视频号内容看着"像通用建议" | 这两块不是薛辉手册原生覆盖 | 属正常：正文已按要求标注来源与等级，不会冒充手册结论 |
