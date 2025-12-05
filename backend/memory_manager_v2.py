# ============================================================
#  MemoryManager V2 (Improved, Thread-Safe, Multi-User, Stable)
# ============================================================

import time
import threading
from typing import List, Dict, Any, Optional
from chromadb import PersistentClient


class MemoryManagerV2:
    """
    Fully redesigned memory manager with:
    - Thread safety
    - User-level isolation
    - Metadata-based filtering
    - Multi-layer memory (long-term, short-term, profile, history)
    - Smart pruning
    - Weighted retrieval logic
    - Backward compatible with V1 interface
    """

    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        collection_name: str = "super_chizuko_memory_v2",
        max_items_per_user: int = 500,
        short_term_expire_sec: int = 60 * 30,   # 30 mins
        history_expire_sec: int = 60 * 10       # 10 mins
    ):
        self.client = PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self.lock = threading.Lock()

        self.max_items_per_user = max_items_per_user
        self.short_term_expire_sec = short_term_expire_sec
        self.history_expire_sec = history_expire_sec

    # --------------------------------------------------------
    # PUBLIC API (保持与 V1 相同的函数名与参数格式)
    # --------------------------------------------------------

    def add_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str = "history",
        tags: Optional[List[str]] = None,
        importance: float = 0.3
    ):
        """
        Memory types:
            - longterm: 永久记忆（喜好、设定）
            - shortterm: 短期记忆（几分钟）
            - history: 最近对话历史
            - profile: 用户档案
        """

        with self.lock:
            ts = int(time.time())
            memory_id = f"{user_id}_{ts}_{abs(hash(content))}"

            self.collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[{
                    "user_id": user_id,
                    "memory_type": memory_type,
                    "tags": tags or [],
                    "importance": float(importance),
                    "created_at": ts,
                    "last_access": ts
                }]
            )

            # 写入时自动清理
            self._prune_user_memory(user_id)

            return memory_id

    def retrieve_relevant_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """智能检索 + 排序"""

        with self.lock:
            # 基础向量检索
            results = self.collection.query(
                query_texts=[query],
                where={"user_id": user_id},
                n_results=limit * 3
            )

            if not results or len(results["ids"][0]) == 0:
                return []

            docs = results["documents"][0]
            ids = results["ids"][0]
            metadatas = results["metadatas"][0]
            scores = results["distances"][0]   # cosine distance

            now = int(time.time())
            processed = []

            for doc, meta, dist, mid in zip(docs, metadatas, scores, ids):

                # 转换 cosine distance -> similarity
                sim = 1 - dist

                recency = 1.0 - min(1.0, (now - meta["last_access"]) / 86400)

                weighted_score = (
                    sim * 0.7 +
                    recency * 0.2 +
                    float(meta.get("importance", 0.3)) * 0.1
                )

                processed.append({
                    "id": mid,
                    "content": doc,
                    "metadata": meta,
                    "score": weighted_score
                })

                # 更新 last_access（LRU）
                meta["last_access"] = now
                self.collection.update(
                    ids=[mid],
                    metadatas=[meta]
                )

            # 排序
            processed.sort(key=lambda x: x["score"], reverse=True)

            # 返回 top N
            return processed[:limit]

    def clear_user_memory(self, user_id: str):
        """清空某用户所有记忆"""
        with self.lock:
            items = self.collection.get(where={"user_id": user_id})
            for i in items["ids"]:
                self.collection.delete(ids=[i])

    # --------------------------------------------------------
    # INTERNAL MAINTENANCE
    # --------------------------------------------------------

    def _prune_user_memory(self, user_id: str):
        """Memory 清理策略"""

        items = self.collection.get(where={"user_id": user_id})
        ids = items["ids"]
        metas = items["metadatas"]

        if not ids:
            return

        now = int(time.time())
        to_delete = []

        # rule 1: 清理 short-term / history 过期
        for mid, meta in zip(ids, metas):
            t = meta["memory_type"]
            age = now - meta["created_at"]

            if t == "shortterm" and age > self.short_term_expire_sec:
                to_delete.append(mid)
            elif t == "history" and age > self.history_expire_sec:
                to_delete.append(mid)

        # rule 2: 超过数量上限后清理 importance 最低的
        if len(ids) - len(to_delete) > self.max_items_per_user:
            survivors = [
                (mid, meta)
                for mid, meta in zip(ids, metas)
                if mid not in to_delete
            ]

            survivors.sort(key=lambda x: x[1].get("importance", 0.3))
            excess = len(survivors) - self.max_items_per_user

            for i in range(excess):
                to_delete.append(survivors[i][0])

        # 执行删除
        if to_delete:
            for mid in to_delete:
                self.collection.delete(ids=[mid])
