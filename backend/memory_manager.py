import datetime
import time
from config import Config

class Memory:
    """记忆类"""
    def __init__(self, memory_id, content, timestamp, state):
        self.memory_id = memory_id
        self.content = content
        self.timestamp = timestamp
        self.state = state

    def is_expired(self):
        """检查记忆是否过期"""
        return time.time() - self.timestamp > Config.MEMORY_EXPIRY_TIME

class MemoryManager:
    """记忆管理器"""
    def __init__(self, chroma_client, embedding_model, collection_name=None):
        self.chroma_client = chroma_client
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """获取或创建Chroma集合"""
        if self.collection_name:
            return self.chroma_client.get_or_create_collection(name=self.collection_name)
        return None
    
    def set_collection_by_name(self, collection_name):
        """根据名称设置当前集合"""
        self.collection_name = collection_name
        self.collection = self._get_or_create_collection()
    
    def add_memory(self, user_msg, assistant_msg, state):
        """添加聊天记忆到向量数据库"""
        if not self.collection:
            print("未设置记忆集合，无法添加记忆")
            return
        
        memory_content = f"用户: {user_msg}\n智子: {assistant_msg}\n状态: {state}"
        embedding = self.embedding_model.encode(memory_content).tolist()
        memory_id = f"memory_{datetime.datetime.now().timestamp()}"
        
        self.collection.add(
            ids=[memory_id],
            documents=[memory_content],
            embeddings=[embedding],
            metadatas=[{
                "timestamp": datetime.datetime.now().isoformat(),
                "user_msg": user_msg,
                "assistant_msg": assistant_msg,
                "state": state
            }]
        )
        print(f"已存储记忆: {user_msg} -> {assistant_msg}...")

    def retrieve_relevant_memories(self, query, n_results=Config.RELEVANT_MEMORIES_COUNT):
        """检索与当前查询相关的记忆"""
        if not self.collection:
            return {"documents": [[]]}
        
        query_embedding = self.embedding_model.encode(query).tolist()
        results = self.collection.query(query_embeddings=[query_embedding], n_results=n_results)
        return results
    
    def check_memory_relevance(self, memory, current_state):
        """检查记忆是否仍然相关"""
        # 如果记忆的情感状态与当前状态差距大，或者时间过期，标记为"遗忘"
        if memory.is_expired():
            return False  # 记忆已过期

        # 检查是否为负面情感记忆，并根据需要删除
        if "失望" in memory.content or "生气" in memory.content:
            return False  # 忘记负面情感相关记忆

        # 其他逻辑：根据优先级、情感权重等进行进一步判断
        if memory.state != current_state:
            return False  # 如果当前状态和记忆的状态差距大，删除该记忆

        return True  # 保留记忆
    
    def clean_up_memory(self):
        """定期清理不相关或过期的记忆"""
        if not self.collection:
            return
            
        try:
            all_memories = self.collection.get()
            if all_memories and all_memories.get('ids'):
                for i, memory_id in enumerate(all_memories['ids']):
                    metadata = all_memories['metadatas'][i] if all_memories.get('metadatas') else {}
                    # 创建临时内存对象用于检查
                    temp_memory = Memory(
                        memory_id=memory_id,
                        content=all_memories['documents'][i] if all_memories.get('documents') else "",
                        timestamp=datetime.datetime.fromisoformat(metadata.get('timestamp', datetime.datetime.now().isoformat())).timestamp() if metadata.get('timestamp') else time.time(),
                        state=metadata.get('state', 'idle')
                    )
                    
                    if not self.check_memory_relevance(temp_memory, current_state="idle"):
                        self.collection.delete(ids=[memory_id])
                        print(f"删除记忆: {memory_id}")
        except Exception as e:
            print(f"清理记忆时出错: {e}")
