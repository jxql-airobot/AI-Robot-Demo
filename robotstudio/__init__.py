# -*- coding: utf-8 -*-
"""
robotstudio — ABB RobotStudio 执行后端 (V6.0)
=============================================
AI Agent 控制 ABB RobotStudio 虚拟工业机器人的适配层。

设计原则（执行层与 AI 决策层分离）：
    Agent -> RobotTool -> RobotStudioBackend -> RobotStudioClient -> 虚拟控制器

通信方案：RAPID Socket TCP（简单文本协议），Python 原生 socket。
无 RobotStudio 时可用 Mock 模式（mock_robotstudio.py）完成全链路测试。
"""
