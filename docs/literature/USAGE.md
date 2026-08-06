# 文献库使用说明

本文档说明怎么把下载好的论文导入 Zotero、配合三个插件使用，以及阅读笔记
怎么维护。全文按"第一次使用"的顺序写，照做即可。

> 2026-08-05 更新：12 篇论文条目、6 个分类、标签和 10 个 PDF 链接已由
> 脚本直接写入 Zotero 数据库（scripts/zotero_import.py）。现在直接打开
> Zotero 就能看到，不需要再手动导入。以下步骤保留作参考，不要重复执行
> 导入脚本（会生成重复条目）。

> 2026-08-05 二次更新：直接写入的"链接附件"在 Zotero 9 里报"无法找到
> 附件"，已用 scripts/fix_attachments_to_stored.py 把 10 个附件全部转成
> Zotero "已存储附件"（PDF 复制到 F:\ZoteroData\storage\<key>\）。现在
> 打开 Zotero 双击条目即可打开 PDF，不再依赖外部路径。F:\AI-Robot-Demo-
> Literature\papers\ 里的原件保留作归档，与 Zotero 内副本相互独立。

> 2026-08-05 三次更新：已存储附件仍报"无法找到附件"，根因是 Zotero 9
> 要求存储目录 key 必须为 8 位大写字母+数字（/^[A-Z0-9]{8}$/），手写
> 的小写混合 key 会导致解析失败。已用 scripts/fix_keys_uppercase.py 把
> 全部条目与分类 key 重生成成大写格式并重建 storage 目录，验证无缺失。

---

## 一、让 Zotero 使用 F:\ZoteroData 数据目录

你的插件和文献库都在 F:\ZoteroData，但 Zotero 目前默认数据目录是
C:\Users\<用户名>\Zotero（旧目录，没有插件），需要切换一次：

1. 关闭 Zotero（如果开着）；
2. 重新打开 Zotero → 菜单栏 编辑 → 设置 → 高级 → 文件和文件夹；
3. 勾选「使用自定义数据目录」；
4. 浏览选择 `F:\ZoteroData`；
5. 点确定，Zotero 会提示重启，重启即可。

如果提示"所选目录非空"或"目录中已有数据"：选「继续使用该目录」即可，
F:\ZoteroData 本身就是完整档案（含 zotero.sqlite）。

验证是否成功：

- 菜单栏出现 Better BibTeX / Jasminum / Translate 相关选项；
- 工具 → 插件 里能看到三个插件；
- 左侧出现空文献库（新档案，需要重新导入论文）。

---

## 二、导入 10 篇论文 PDF

（已自动完成并转为已存储附件，以下为手动方法参考）

PDF 位置：`F:\AI-Robot-Demo-Literature\papers\<分类>\`

两种方式任选：

### 方式 A：拖拽导入（默认，PDF 会复制进 Zotero storage）

1. 打开 Zotero，在左侧新建分类（见第三节）；
2. 从文件夹里把 PDF 拖进 Zotero 中间列表；
3. Zotero 会自动联网抓取元数据（arXiv 论文一般能自动补全标题作者）；
4. 抓取失败的：右键条目 → 查找 PDF 元数据，或右键 → 通过标识符添加条目，
   输入 arXiv 编号（如 2210.03629）补全。

### 方式 B：链接附件（PDF 留在文献库原位，不复制）

想保持 F:\AI-Robot-Demo-Literature\papers\ 是唯一 PDF 副本：

1. 右键 Zotero 列表 → 新建条目 → 常规条目，先建空条目；
2. 右键该条目 → 添加附件 → 链接到文件 → 选对应 PDF；
3. 再用「查找 PDF 元数据」补全信息。

注意：方式 B 依赖 F 盘路径，F:\AI-Robot-Demo-Literature 文件夹不要改名
或移动。

---

## 三、建分类和标签

建议与文献库目录保持一致：

分类（Collection）：

    AI-Robot-Demo Literature
    ├── 01 LLM Robot Planning
    ├── 02 Robot Agent
    ├── 03 RAG Knowledge
    ├── 04 Robot Software Architecture
    └── 05 Embodied AI

标签（Tags）：LLM、Agent、RAG、Robot Planning、Industrial Robot、
Embodied AI、Software Architecture

选中条目后，在右侧"标签"栏输入即可；一次可多选条目批量加标签。

---

## 四、Jasminum（中文文献助手）

用途：把知网/万方/维普下载的中文 PDF 导入 Zotero 时，自动抓取中文元数据
并把附件重命名成中文标题（如 王田苗_我国工业机器人技术现状.pdf）。

步骤：

1. 从知网下载 PDF（直接下载即可，文件名乱码没关系）；
2. 拖进 Zotero；
3. 右键该条目 → Jasminum → 抓取知网元数据（菜单名以实际插件为准）；
4. 插件联网匹配后自动填中文标题、作者、期刊、年份，并重命名附件；
5. 检查无误后加标签。

适用文献：王田苗（机械工程学报）、谭民（自动化学报）等中文期刊论文。

---

## 五、Better BibTeX（导出参考文献）

用途：给论文或 LaTeX 导出稳定引用键（cite key）的 .bib 文件。

步骤：

1. 在 Zotero 里选中要导出的条目；
2. 右键 → 导出条目；
3. 格式选「Better BibTeX / BibLaTeX」→ 确定，保存 .bib 文件；
4. 键名格式默认类似 `ahn2022do`，稳定不变。

说明：本科 Word 论文的参考文献列表可以手动整理，不强制用 BibTeX；这个
插件主要是为以后 LaTeX 写作和硕士阶段做准备。

---

## 六、Translate for Zotero（读原文翻译）

用途：打开 PDF 后选中段落，一键翻译，读英文论文逐段对照。

步骤：

1. 在 Zotero 里双击打开 PDF；
2. 选中要翻译的段落 → 点工具栏翻译按钮（或右键 → 翻译）；
3. 在设置里可切换翻译服务（免费服务够用；DeepL 需要 API key）。

与阅读笔记的分工：插件负责"逐句看懂原文"，reading_notes 里的中文笔记
负责"归纳存留、关联项目"。

---

## 七、阅读笔记怎么用

文件都在项目 `docs/literature/`（已提交 Git）：

    docs/literature/
    ├── USAGE.md              本说明
    ├── literature_index.md   文献索引 + 22 篇参考文献分级
    ├── reading_plan.md       8 篇核心论文阅读计划（含答辩话术）
    ├── missing_papers.md     缺失文献清单
    ├── templates/            笔记模板
    └── reading_notes/        中文阅读笔记（每篇一个 md）

流程：

1. 读论文前先看 reading_notes 里对应笔记的"核心思想"和"与 AI-Robot-Demo
   关系"，快速定位重点；
2. 用 Zotero + Translate 读原文，验证笔记；
3. 按 reading_plan.md 的"3 分钟讲清楚"标准自查；
4. 有新理解就更新笔记的"个人理解"和"是否可以用于论文答辩"。

阅读方式有两种：

1. **Zotero 里直接看**：每篇论文条目下都挂了一条「中文阅读笔记」子笔记
   （右侧 Notes 标签里），双击就是排版好的中文；另有一条独立笔记
   「文献库中文笔记索引」；
2. **浏览器看合集**：双击打开 论文中文导读.html，12 篇中文笔记按顺序
   排版在一页，字体大、适合阅读。

PDF 原件在 `F:\AI-Robot-Demo-Literature\papers\`，不入 Git。

---

## 八、常见问题

Q：Zotero 里看不到插件？
A：说明数据目录还是 C 盘旧目录，按第一节重新切换到 F:\ZoteroData 并重启。

Q：PDF 拖进去标题是乱的？
A：右键条目 → 查找 PDF 元数据；或删除条目，用"通过标识符添加条目"输入
arXiv 编号/DOI 重建。

Q：Jasminum 抓取失败？
A：确认网络能访问知网；右键里 Jasminum 菜单存在；知网对自动化有反爬，
失败就手动填关键字段（标题、作者、年份、期刊）。

Q：F 盘文献库文件夹能移动吗？
A：不能。Zotero 里用"链接到文件"的条目依赖 F:\AI-Robot-Demo-Literature
路径；移动后链接会断，需要重新关联。
