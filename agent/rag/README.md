# RAG 语义记忆设计 (V5.3)

> 状态：第三步完成（Agent / GUI 集成完成，V5.3 功能完整）。

## 1. 目标

把 V2 的关键词记忆升级为**语义检索**：

- 记忆写入时同步生成向量（嵌入）
- 任务查询时用向量相似度召回语义相近的记忆
- 保留 V2 关键词检索作为兜底（混合检索）

示例：用户问「那个红色的东西在哪」时，能召回记忆
`红色零件 -> 右侧区域（视觉识别）`，即使没有命中关键词。

## 2. 架构设计

```
记忆写入（memory_tool / vision_node 写入）
   → SQLite 记忆表（V2 原样，不修改）
   → RAG 同步：文本 → embedder 向量 → vector_store 存副本（新表）

记忆查询（Agent 规划 / GUI 记忆页）
   → 任务文本 → 向量 → cosine 相似度 top-k
   → 关键词 LIKE 检索（V2 原样）
   → 混合融合（向量为主，关键词兜底）→ 注入 Planner / memory_tool
```

## 3. 技术选型

| 项 | 选型 | 理由 |
| --- | --- | --- |
| 嵌入模型 | `bge-small-zh-v1.5`（中文小模型，~100MB） | 中文效果好、体积小、CPU 可跑 |
| 推理框架 | sentence-transformers（CPU） | 开箱即用，模型加载/编码一条龙 |
| 模型来源 | ModelScope 下载到 `~/.ai_robot/models/` | 国内网络可用（同 YOLO 权重方案） |
| 向量存储 | SQLite 新表 `memories_embeddings` + numpy 余弦检索 | demo 数据量小，不引入向量数据库服务 |
| 依赖 | torch（CPU 版）+ sentence-transformers | 需 pip 安装（约 500MB，磁盘充足） |

## 4. 文件规划

| 文件 | 作用 |
| --- | --- |
| `agent/rag/__init__.py` | 子模块声明 |
| `agent/rag/embedder.py` | 模型懒加载 + embed(texts) + 单例缓存 |
| `agent/rag/vector_store.py` | 建表 / 写入向量 / 余弦检索 top-k |
| `agent/rag/retriever.py` | 混合检索：向量 + 关键词，融合去重 |
| `agent/rag/model_download.py` | ModelScope 下载脚本（首次运行自动） |
| `agent/rag/README.md` | 本文档 |

## 5. 集成改动（只新增/扩展，不修改 V1-V4）

- `agent/tools/memory_tool.py`：写记忆时同步向量；新增 `{"semantic": "查询文本"}` 语义查询
- `agent/planner.py`：上下文注入改用 retriever（向量为主，关键词兜底）
- `gui/app.py` 记忆页：显示语义检索结果与相关度
- `agent/core.py`：Agent 组装 retriever，无模型时自动降级为关键词检索

## 6. 兼容性与风险

- **零修改**：memory.py / llm.py / robot.py / ROS2 节点 / Gazebo
- **降级**：模型未下载或加载失败时，自动回退 V2 关键词检索，功能不阻塞
- **依赖**：首次需安装 torch（CPU）+ sentence-transformers 并下载模型（~400MB）
- **数据**：向量存新表，原记忆表不动，老记忆可一键补建向量

## 7. 后续步骤

1. 安装依赖 + 下载模型
2. 实现 embedder / vector_store / retriever
3. 集成 memory_tool / planner / GUI
4. 测试 + 提交 + 打 tag `v5.3-rag`
