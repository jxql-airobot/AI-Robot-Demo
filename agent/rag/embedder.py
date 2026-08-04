# -*- coding: utf-8 -*-
"""
embedder.py — 嵌入模型封装 (V5.3)
=================================
懒加载 sentence-transformers 模型，输出 L2 归一化向量（余弦 = 点积）。
模型名/设备/路径全部来自 config.json。
"""

import numpy as np

from agent.rag.config import load_config


class Embedder:
    """文本嵌入器"""

    def __init__(self, cfg=None):
        self.cfg = cfg or load_config()
        em = self.cfg["embedding_model"]
        self.model_path = em["model_path"]
        self.device = em.get("device", "cpu")
        self._model = None

    @property
    def available(self):
        """模型可加载返回 True，否则 False（调用方降级为关键词检索）"""
        try:
            self._get_model()
            return True
        except Exception:
            return False

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # 延迟导入

            self._model = SentenceTransformer(self.model_path, device=self.device)
        return self._model

    def embed(self, texts):
        """把文本（str 或 list[str]）编码成归一化向量矩阵"""
        model = self._get_model()
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            dim = model.get_sentence_embedding_dimension()
            return np.zeros((0, dim), dtype=np.float32)
        vecs = model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vecs, dtype=np.float32)
