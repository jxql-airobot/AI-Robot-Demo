# 论文关联知识库

本目录把论文、项目模块和论文章节串成一张网，用途：

- 写论文第 2 章（相关技术）时快速找到对应文献；
- 答辩前按模块复习"我的设计参考了什么"；
- 软件工程硕士复试时讲清技术脉络；
- 为未来具身智能方向留一份结构化索引。

## 知识库结构

```
论文（22 篇参考文献 + 文献库扩展论文）
  ↓ 关联
项目模块（Agent / RAG / RobotTool+Backend / 安全约束 / 实验）
  ↓ 关联
论文章节（第 1~6 章）
  ↓ 输出
答辩问题 + 术语表
```

## 文件清单

| 文件 | 内容 |
| --- | --- |
| [thesis_map.md](thesis_map.md) | 22 篇参考文献 ↔ 论文章节 ↔ 项目模块映射总表 |
| [module_cards.md](module_cards.md) | 按项目模块组织的知识卡（论文-观点-实现-章节-答辩一句话） |
| [defense_qa.md](defense_qa.md) | 答辩高频问题与回答要点 |
| [glossary.md](glossary.md) | 核心术语表 |

## 核心关联速览

```
Agent 思想      ← ReAct [15]、Agent 综述 [16]、ChatGPT for Robotics
语言→机器人技能  ← SayCan [6]
知识增强        ← RAG [19]
软件架构        ← 软件架构实践 [21]、软件工程导论 [20]、设计模式 [22]、映射研究（扩展）
底层通信        ← ROS2 [10]、Gazebo [11]、RobotStudio [12]
工具调用        ← Toolformer [17]、HuggingGPT [18]
未来方向        ← PaLM-E [8]、RT-2 [9]、Inner Monologue [7]、具身 AI 综述、Foundation Models
```

## 使用建议

1. 写第 2 章时：按 thesis_map.md 的"对应章节"列取文献；
2. 答辩前：按 module_cards.md 逐个模块过一遍"答辩一句话"；
3. 复试展示：用 README 的核心关联速览讲 3 分钟技术路线。
