# -*- coding: utf-8 -*-
"""
config.py — RobotStudio 配置加载 (V6.0)
=======================================
从 config.json 读取连接参数（主机/端口/超时/后端模式），不硬编码。
backend: "mock"（无 RobotStudio 时测试）| "real"（连接真实虚拟控制器）
"""

import copy
import json
import os

RS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(RS_DIR, "config.json")

DEFAULTS = {
    "host": "127.0.0.1",
    "port": 30000,
    "timeout_seconds": 5.0,
    "backend": "mock",
}


def load_config(path=None):
    """读取配置：文件缺失或字段缺失时用默认值"""
    cfg = copy.deepcopy(DEFAULTS)
    config_path = path or DEFAULT_CONFIG_PATH
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as fh:
                data = json.load(fh)
            cfg.update({k: data[k] for k in cfg if k in data})
        except (json.JSONDecodeError, OSError):
            pass
    return cfg
