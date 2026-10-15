# 短视频运营 skill 套件（dsh-shortvideo-suite）

把**两本手册**变成一套能讲课、能操刀、能长期陪跑的 agent 能力：
**7 个 skill + 一个 48 段的知识库 + 两个 Office 交付物生成脚本**。

> **制作方：由 NICKIE XIE 谢宇翔 制作 · 2026 年 · 合作联系：18815602213（微信同）**
>
> 装到别的机器 / 别的 Agent：看 **[INSTALL.md](INSTALL.md)**（含一段可直接转发给另一个 Agent 的安装指令）。
> 业务规格（宪法）在 [docs/framework.md](docs/framework.md)；路由定义在 [docs/skill-routing.md](docs/skill-routing.md)。

## 七个 skill 的分工

| skill | 什么时候用 | 产出 |
|---|---|---|
| `shortvideo-coach` | 要从零做一个账号、要一步步带着做、要长期陪跑 | 9 轮拷问式问诊 → 账号档案（落盘）→ 30 天作战表 → 日更选题/脚本/拍摄清单 → 周复盘 |
| `shortvideo-advisor` | 诉求含糊、"我想做短视频"、"从哪开始"、要学习路径 | 诊断 → 角色判定 → 总规划 → 交接；讲师模式带学与批改 |
| `shortvideo-launch` | 定位、赛道、账号搭建、选题、30 天排期、每日动作 | 账号策划单、30 天排期表、首月选题清单 |
| `shortvideo-production` | 脚本、口播表现力、分镜、拍摄、剪辑、发布 | 脚本表、分镜表、发布前检查清单 |
| `shortvideo-growth` | DOU+ 投放、数据指标、AB Test、直播 | 投放决策表、数据诊断表、AB Test 记录 |
| `shortvideo-agency` | 代运营接单、客户诊断、报价、合同、验收、产能 | 需求诊断表、报价单、验收单 |
| `shortvideo-team` | 团队岗位分工、SOP、拆片会、审片、绩效 | 团队配置表、SOP 清单、审片流程卡、绩效表 |

**边界要点**：`shortvideo-advisor` = **学**（要理解、要评估）；`shortvideo-coach` = **做**（要产出、要陪跑）。
两者都可能被"我想做短视频"命中 → 按"要理解还是要产出"分流；要产出但信息不足 → coach 先问诊。

## 五条强制行为规则（摘要，细则见 docs/framework.md）

1. **R1 诊断先于方案** —— 缺哪项问哪项，不许脑补、不许用行业均值代替。
2. **R2 分级贯穿输出** —— 统一八级可信度刻度（【官方】/【公开表述】/【官方公开课】/【口碑好评】/【第三方转述】/【网络流传未核实】/【本手册推断】/⚠️已失效）；推断内容必须说明"不是原话"。
3. **R3 边界诚实** —— 手册缺口先说明没有，再给标注过的通用做法。
4. **R4 数据挂时效** —— 引用具体数值必须附来源时点与"以官方当前数据为准"。
5. **R5 平台分轨** —— 抖音 = 原生；视频号 = 非原生，来源不同标注不同。

## 目录结构（扁平，必须保持）

```text
shortvideo-suite/                 ← 套件根 = 发现根
  shortvideo-coach/SKILL.md       ← 7 个 skill 是根目录的直接子目录
  shortvideo-advisor/SKILL.md
  shortvideo-launch/SKILL.md
  shortvideo-production/SKILL.md
  shortvideo-growth/SKILL.md
  shortvideo-agency/SKILL.md
  shortvideo-team/SKILL.md
  knowledge/                      ← 与 skill 目录同级（skill 用 <skill-directory>/../knowledge/ 引用）
    index.md                      ← 导航表：什么问题读哪几个文件
    问诊清单.md                    ← 9 轮拷问问诊题库（coach 专用）
    薛辉手册/（33 段）             ← 通用短视频运营方法论（抖音原生）
    建材矩阵手册/（15 段）          ← 第二本手册：建材行业矩阵运营实证
    矩阵/01-矩阵方法论-建材行业实证.md  ← 矩阵方法论（补薛辉手册的缺口）
    平台差异-抖音与视频号.md         ← ⚠️ 非手册内容（视频号补充）
    矩阵-待补充.md                  ← 历史占位（已被 矩阵/01 取代）
  scripts/                        ← 校验器、审查器、安装器、两个 Office 生成脚本
  templates/                      ← 空模板：账号档案(.md/.json)、诊断与方案、新 skill 骨架
  docs/                           ← framework.md（宪法）、skill-routing.md、examples/（JSON 样例）
  tools/                          ← 手册再投喂工具：extract_docx.py、split_manual.py、两个测试脚本
  plugin/index.mjs  cordis.patch.yml  package.json
  README.md  INSTALL.md
```

**为什么必须扁平**：正文里写的是 `<skill-directory>/../knowledge/…`，而 `<skill-directory>` 是运行时的资源基目录。
只有"skill 目录的直接父目录同时装着 knowledge/ 与 scripts/、templates/"时，这条路径在**源码、扁平安装、插件**三种形态下才都成立。
改成常见的 `skills/<name>/` 布局会让部署后断链——本套件第一版就是这样，被 `review_skills.py` 抓出来后改掉了。

## 用法

### A. 装到发现根（自用）

```powershell
<python> scripts\install.py --dry-run     # 先看计划
<python> scripts\install.py               # 装到 $DSH_HOME\skills
<python> scripts\install.py --root <某个项目的>\.dsh\skills
```

### B. 插件分发 / C. 其他 Agent / D. 无技能支持的 Agent

见 [INSTALL.md](INSTALL.md)。**本包不含任何具体用户的数据**：用户实际产生的账号档案写在
`<工作区>/账号/<账号名>/` 下，包内 `templates/` 只有空表单。

## 校验（每次改完必跑）

```powershell
<python> scripts\validate_skills.py      # ① frontmatter 语法契约（对齐加载器真实规则）
<python> scripts\review_skills.py        # ② 内容契约：description 逐字一致、引用断链、结构、红线
node tools\plugin-smoke.mjs .            # ③ 插件契约与 resourceBase 不变式
<python> tools\test_deliverable_kinds.py # ④ 8 种交付物 kind 全量跑通
```

四个检查器的分工：① 管 frontmatter（加载器会静默忽略的部分）；② 管校验器管不到的
（引用的知识库文件是否存在、红线内容是否出现、description 是否与路由表逐字一致）；
③ 管分发形态（候选是否满足注册表校验、`<resourceBase>/../knowledge` 是否存在）；
④ 管交付物脚本的 8 种 `--kind`。

## 交付物：Word / Excel

两个脚本吃 JSON、吐 Office 文件；**不要在 skill 里手写 python-docx/openpyxl**。

```powershell
<python> scripts\make_docx.py  --kind plan|script|acceptance|report --input x.json --output y.docx
<python> scripts\make_xlsx.py  --kind schedule|quote|diagnosis|metrics --input x.json --output y.xlsx
```

JSON 结构见 [docs/examples/](docs/examples/) 的四个可直接运行的样例（起号方案书、排期表、报价单、验收单）。
脚本会校验结构并给出可执行的报错；输出必须是不存在的新文件（或用 `--force`）。

## 知识库

- 单一真源（套件外的工作区 `knowledge/`）：`薛辉短视频运营资料-培训版.md`（95,525 字符）、
  `建材行业短视频矩阵账号运营手册.md`（50,857 字符），用 `tools/extract_docx.py` 提取、`tools/split_manual.py` 拆分
  （后者自动识别两种文档风格：带标题样式的 `## `，和不带样式的 `第 1 章　`/`附录 A　`）
- 入门必读：`knowledge/index.md`（导航表）、`薛辉手册/03`（分级）、`薛辉手册/27-附录C`（缺口与过期数据）、
  `建材矩阵手册/01`（起点产能测算 + 分级）、`建材矩阵手册/15-附录-F`（建材手册自己的缺口）

## 当前状态

**已验证**：7 个 skill 通过语法与内容双检查；插件契约与 resourceBase 不变式成立；
交付物 8 种 kind 全通过（4 正例 + 5 反例被拦下）；docx 经结构检查与渲染检查（中文正常）；
安装链路在测试根验证过（安装后相对路径全部可解析）。

**待补（已知缺口，skill 里已如实处理）**：

| 缺口 | 现状 |
|---|---|
| 拆片会第 11 个维度 | 手册记作"11 项"但公开清单只有 10 项 |
| 拆片会时长/轮值/表格实样 | 推演设计，需实况校准 |
| 绩效指标权重 | 需要用户现有考核办法与薪资结构 |
| 剪映操作教学 | 只有功能清单，指向剪映官方教程 |
| 直播逐字话术 | 只有四套结构骨架 |
| 五大型 ↔ 六类脚本模型对照 | 手册无对照表，按"先认类型再选模板"处理 |
| 非建材行业的行业实证层 | 建材手册的品类/客群/话术是建材专属，其他行业需替换并标注"结构套用" |
| 视频号 | 两本手册都不是原生资料，按来源分别标注 |

## 资料来源与免责声明

本仓库包含两份资料的知识库文本，来源与权利归属不同，请分开看待：

1. **《薛辉短视频运营资料-培训版》**（`knowledge/薛辉手册/`，33 段）
   这是**第三方公开可访问素材的整理**，不是原始付费课程内容——整理者自述"仅收录公开可访问内容，
   未收录任何付费课程正文、逐字稿或盗版资源"，并对每条结论做了五级可信度标注。
   其中涉及的方法论、课程体系与观点，**著作权归原作者/权利人所有**；本仓库仅作学习与研究之用，
   不代表权利人授权、认可或合作。完整出处清单见 `knowledge/薛辉手册/26-附录B-完整来源清单.md`。
2. **《建材行业短视频矩阵账号运营手册》**（`knowledge/建材矩阵手册/`，15 段）与
   `knowledge/矩阵/01-矩阵方法论-建材行业实证.md`
   由本套件作者自行调研整理，含【官方】/【公开表述】/【口碑好评】/【第三方转述】/▸ 推演设计等分级标注。

**给使用者的提醒**：知识库里的具体数值（流量占比、流量池场观、价格、粉丝量等）来自特定时点的
整理，平台规则持续变化，请以官方当前口径为准。用于商业交付前请自行确认合规性。
若权利人或任何第三方认为本仓库内容不妥，请通过下方联系方式告知，会立即处理。

**制作方**：NICKIE XIE 谢宇翔 · 2026 年 · 合作联系：18815602213（微信同）
