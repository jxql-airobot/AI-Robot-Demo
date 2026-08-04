# Git 提交规范

## 1. 提交信息格式

采用 Conventional Commits 风格：

```
<type>(<scope>): <description>
```

### 常用 type

| type | 用途 | 示例 |
| --- | --- | --- |
| `feat` | 新功能 | `feat(agent): add task planning agent` |
| `fix` | 修复 Bug | `fix(gui): improve interface display` |
| `docs` | 文档 | `docs: update architecture document` |
| `refactor` | 重构（不改功能） | `refactor(rag): simplify retriever merge logic` |
| `chore` | 杂项（依赖/配置） | `chore: pin numpy to 1.26.4` |
| `test` | 测试 | `test(rag): add semantic recall case` |
| `perf` | 性能优化 | `perf(controller): reduce nav oscillation` |

### scope 建议

`core`（V1/V2 核心）、`gui`、`agent`、`rag`、`ros2`、`launcher`、`docs`

## 2. 当前 Git 历史分析

共 31 个提交，按类型分布：

| 类型 | 数量 | 说明 |
| --- | --- | --- |
| feat | 13 | V1-V5.3 各阶段功能 |
| fix | 4 | 记忆容错、乱码、task_cli 等待、启动清理 |
| docs | 10 | 学习记录、路线图、设计文档 |
| chore | 1 | 移除 README 个人内容 |
| 早期未规范 | 3 | first demo / launcher / study log（无前缀） |

早期（V1-V2）部分提交未遵循规范（如 `3442240 first AI robot demo`、
`a9b039f add desktop launcher`），V3 起逐步规范，V5.x 已完全遵循。

## 3. 后续提交规范

1. 所有提交使用 `<type>(<scope>): <描述>`，描述用英文动词开头（add/fix/update/refactor）
2. 一个提交只做一件事（功能 / 修复 / 文档分开）
3. 每完成一个小版本打 Tag：`v4.0-gazebo`、`v5.1-gui`、`v5.2-agent`、`v5.3-rag`
4. 敏感文件不入库：`.env`、`database.db`、`__pycache__`（已在 .gitignore）
5. 提交前自测：`python -m py_compile` + 相关测试脚本

## 4. 分支策略

- 个人开发阶段：单一 `main` 分支 + 版本 Tag
- 开源协作阶段：`main` 保护 + `feature/*` 分支 + PR 合并
