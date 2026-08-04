# RAG 语义记忆设计

## 1. 功能介绍

RAG 模块（`agent/rag/`）把 V2 的关键词记忆升级为**语义检索**：

- 记忆写入时生成向量并存入 SQLite 向量表
- 查询时用向量余弦相似度召回语义相近的记忆
- 保留 V2 关键词检索作为兜底（混合检索，结果带来源标记）

核心价值：用户问"那个红色东西在哪里"时，即使不包含"零件"关键词，
也能召回"红色零件 → 位于右侧区域"这条记忆。

## 2. 技术选择原因

| 项 | 选型 | 原因 |
| --- | --- | --- |
| 嵌入模型 | `bge-small-zh-v1.5` | 中文效果好、体积小（~100MB）、CPU 可推理 |
| 推理框架 | sentence-transformers | 开箱即用，模型加载/编码一条龙 |
| 向量存储 | SQLite 新表 + numpy 余弦 | demo 数据量小，不引入 FAISS/Chroma 等外部服务 |
| 模型来源 | ModelScope | 国内网络可用（与 YOLO 权重同方案） |
| 配置 | `config.json` | 模型名/设备/路径/来源全部配置化，不硬编码 |

## 3. 数据流程

```
记忆写入（memory_tool / vision_node）
  → SQLite 记忆表（V2 原样）
  → embedder 编码 → vector_store 存向量副本

记忆查询
  → 语义检索：任务文本 → 向量 → 余弦 top-k
  → 关键词检索：LIKE 模糊匹配（V2 原样）
  → 混合融合（语义优先，按 topic+content 去重）→ 返回带 source 的结果
```

### 向量表结构

```sql
CREATE TABLE memories_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    embedding BLOB NOT NULL   -- float32 向量
);
```

## 4. 当前实现状态

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `agent/rag/config.json` | ✅ | 模型配置（name/device/model_path/model_source） |
| `agent/rag/embedder.py` | ✅ | 懒加载 + 归一化向量编码 |
| `agent/rag/vector_store.py` | ✅ | 建表 / rebuild / 余弦检索 top-k |
| `agent/rag/retriever.py` | ✅ | 混合检索（语义 + 关键词，带 source） |
| `agent/rag/model_download.py` | ✅ | ModelScope 下载（失败回退 HF 镜像） |
| `agent/rag/test_rag.py` | ✅ | 语义相近用例测试通过 |

**已通过的核心测试**：

```
记忆：红色零件 → 位于右侧区域
查询："那个红色东西在哪里"
结果：top1 = 红色零件 → 位于右侧区域（来源：语义检索）✅
```

## 5. 未来扩展方向

- Agent/planner 上下文注入 RAG 检索结果（✅ 已完成）
- GUI 记忆页展示语义检索结果（来源/内容，不显示复杂相似度数字）（✅ 已完成）
- 记忆增量更新（新增记忆只嵌入新条目，不重建全表）
- 向量索引升级（数据量大时引入 FAISS/Chroma）
- 多语言/更大模型（bge-large 等）切换
