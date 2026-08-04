# -*- coding: utf-8 -*-
"""
config.py — RAG 配置加载 (V5.3)
===============================
从 config.json 读取嵌入模型配置（名称/设备/路径/来源），不硬编码。
"""

import copy
import json
import os

RAG_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(RAG_DIR, "config.json")

DEFAULTS = {
    "embedding_model": {
        "name": "bge-small-zh-v1.5",
        "device": "cpu",
        "model_path": "~/.ai_robot/models/bge-small-zh-v1.5",
        "model_source": "modelscope",
    }
}


def load_config(path=None):
    """读取 RAG 配置：文件不存在或字段缺失时用默认值"""
    cfg = copy.deepcopy(DEFAULTS)
    config_path = path or DEFAULT_CONFIG_PATH
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as fh:
                data = json.load(fh)
            em = data.get("embedding_model") or {}
            cfg["embedding_model"].update(em)
        except (json.JSONDecodeError, OSError):
            pass
    em = cfg["embedding_model"]
    em["model_path"] = os.path.expanduser(em.get("model_path", DEFAULTS["embedding_model"]["model_path"]))
    return cfg
