# 贡献指南

感谢你考虑为 AI-Robot-Demo 贡献代码！请遵循以下规范。

## 开发流程

1. Fork 本仓库并克隆到本地
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 开发完成后自测（见下方「测试要求」）
4. 提交（遵循 Conventional Commits，见 `docs/git_conventions.md`）
5. 推送分支并提交 Pull Request

## 提交规范

```text
feat(scope): description
fix(scope): description
docs: description
refactor(scope): description
```

scope 建议：`core / gui / agent / rag / ros2 / launcher / experiments / docs`

## 测试要求

- 修改 Python 文件后：`python -m py_compile <file>`
- Agent 相关改动：`python agent/test_agent.py`（Windows/WSL 均可）
- RAG 相关改动：`python3 agent/rag/test_rag.py` 与 `python3 agent/test_agent_rag.py`（WSL）
- ROS2 相关改动：`python3 gui/test_agent_backend.py`（WSL + 仿真系统）
- GUI 改动：`python3 gui/test_app.py`（WSL）

## 环境注意

- numpy 必须锁定 1.26.4（勿升级到 2.x，cv_bridge 不兼容）
- RAG 依赖（torch / sentence-transformers）仅在 WSL 需要
- 敏感文件（.env / database.db）不入库

## Issue 提交

- 说明复现步骤、期望行为、实际行为
- 附上相关日志（无敏感信息）
