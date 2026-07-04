"""
第4章产出：Memory
==================

补全这个类，让 tests/test_memory.py 全部通过。
"""

from __future__ import annotations

import json
import math
import os
from openai import OpenAI

from llm import LLMClient


class Memory:
    def __init__(self, llm: LLMClient):
        self._entries: list[tuple[str, list[float]]] = []
        self._llm = llm
        self._embedding_available = True  # 标记 embedding API 是否可用
        self._embedding_client = None  # 独立的 embedding API 客户端

    def _get_embedding(self, text: str) -> list[float] | None:
        """获取文本的向量表示。embedding API 不可用时返回 None。"""
        if not self._embedding_available:
            return None
        try:
            # 支持独立的 embedding API 配置
            embedding_base_url = os.getenv("EMBEDDING_BASE_URL")
            embedding_api_key = os.getenv("EMBEDDING_API_KEY")

            if embedding_base_url and embedding_api_key:
                # 使用独立的 embedding 客户端（懒加载）
                if self._embedding_client is None:
                    self._embedding_client = OpenAI(
                        base_url=embedding_base_url,
                        api_key=embedding_api_key,
                    )
                client = self._embedding_client
            else:
                # 使用主 LLM 客户端
                client = self._llm.client

            resp = client.embeddings.create(
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                input=text,
            )
            return resp.data[0].embedding
        except Exception:
            self._embedding_available = False
            return None

    @staticmethod
    def _keyword_score(query: str, text: str) -> float:
        """基于关键词重叠的简单相似度（embedding API 不可用时的降级方案）。"""
        query_words = set(query)
        text_words = set(text)
        if not query_words:
            return 0.0
        intersection = query_words & text_words
        return len(intersection) / len(query_words)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """余弦相似度。"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def add(self, text: str) -> None:
        """存入一条记忆。"""
        embedding = self._get_embedding(text)
        # embedding 为 None 时存空列表，search 时会走关键词降级
        self._entries.append((text, embedding or []))

    def search(self, query: str, k: int = 3) -> list[tuple[float, str]]:
        """检索最相关的 k 条，返回 [(similarity, text), ...]。"""
        if not self._entries:
            return []

        # embedding API 不可用时，使用关键词降级
        if not self._embedding_available:
            scored = []
            for text, _ in self._entries:
                sim = self._keyword_score(query, text)
                scored.append((sim, text))
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[:k]

        # embedding 可用时，使用向量相似度
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return []
        scored = []
        for text, emb in self._entries:
            if not emb:
                continue
            sim = self._cosine_similarity(query_embedding, emb)
            scored.append((sim, text))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:k]

    def save(self, path: str) -> None:
        """持久化到 JSON 文件。"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False)

    def load(self, path: str) -> None:
        """从 JSON 文件加载。"""
        with open(path, "r", encoding="utf-8") as f:
            self._entries = json.load(f)
