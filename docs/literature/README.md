# 论文中文阅读备份系统

本目录存放毕业论文相关文献的中文阅读笔记，作为个人学习资料。PDF 原文按
分类存放在 F 盘文献库：`F:\AI-Robot-Demo-Literature\papers\`（不入 Git，
避免大文件入库）。笔记只做理解和归纳，不生成正式引用，不修改论文内容。

## 目录结构

```
docs/literature/
├── README.md
├── templates/
│   └── paper_note_template.md    论文阅读笔记模板
├── reading_notes/                中文阅读笔记（每篇论文一个 md）
└── related_work/                 相关工作资料
```

论文 PDF 分类（F:\AI-Robot-Demo-Literature\papers\）：

1. `01_LLM_Robot_Planning/`：LLM 用于机器人任务规划；
2. `02_Robot_Agent/`：机器人 Agent 设计；
3. `03_RAG_Knowledge/`：知识增强（RAG）；
4. `04_Robot_Software_Architecture/`：机器人软件架构；
5. `05_Embodied_AI/`：具身智能与未来方向。

## 笔记格式

每篇论文一个 Markdown 文件，命名规则：

    <第一作者拼音>-<年份>-<论文关键词>.md

例如：

    lewis-2020-retrieval-augmented-generation.md

内容按 templates/paper_note_template.md 的八个部分填写：基本信息、研究
背景、核心思想、系统架构、技术方法、实验设计、与 AI-Robot-Demo 关系、
个人理解。

## 当前文献清单（2026-08-05）

10 篇阅读笔记已完成（ReAct、SayCan、Inner Monologue、RAG、PaLM-E、RT-2、
ChatGPT for Robotics、机器人软件架构映射研究、具身 AI 综述、Foundation
Models in Robotics），2 篇为占位（IEEE 付费论文、ROS 书籍）。完整清单见
[reading_notes/00_索引.md](reading_notes/00_索引.md)，PDF 在
F:\AI-Robot-Demo-Literature\papers\。

Zotero 插件配合（本机 Zotero 9.0.6 + Better BibTeX 9.0.49 / Jasminum
1.1.37 / Translate 2.4.5）：Jasminum 用于中文文献入库，Better BibTeX
管理引用键，Translate 负责读原文时的逐段翻译。插件只能在 Zotero 界面
使用，命令行无法直接调用。

## 维护记录

- 2026-08-05：建立目录结构与阅读模板（与 F:\AI-Robot-Demo-Literature
  文献库对应）。
- 2026-08-05：完成 10 篇阅读笔记、2 篇占位；记录 Zotero 插件用法。
- 2026-08-05：生成 missing_papers.md（缺失文献清单）、literature_index.md
  （22 篇参考文献分级映射）、reading_plan.md（8 篇核心论文阅读计划）。
