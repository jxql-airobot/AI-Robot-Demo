# -*- coding: utf-8 -*-
"""
model_download.py — 嵌入模型下载 (V5.3)
=======================================
优先 ModelScope（国内可用），失败后回退 HuggingFace 镜像。
模型路径由 config.json 配置。
"""

import os

from agent.rag.config import load_config


def ensure_model(cfg=None):
    """确保模型已下载到配置路径，返回模型目录"""
    cfg = cfg or load_config()
    em = cfg["embedding_model"]
    model_path = em["model_path"]
    name = em["name"]

    if os.path.isdir(model_path) and any(os.scandir(model_path)):
        return model_path

    os.makedirs(model_path, exist_ok=True)
    source = em.get("model_source", "modelscope")

    if source == "modelscope":
        try:
            from modelscope import snapshot_download

            snapshot_download(f"BAAI/{name}", local_dir=model_path)
            return model_path
        except Exception as exc:
            print(f"[RAG] ModelScope 下载失败({exc})，回退 HuggingFace 镜像...")

    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from huggingface_hub import snapshot_download as hf_download

    hf_download(f"BAAI/{name}", local_dir=model_path)
    return model_path


def main():
    path = ensure_model()
    print(f"[RAG] 模型就绪: {path}")


if __name__ == "__main__":
    main()
