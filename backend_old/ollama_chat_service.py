import os
import json
import datetime
from flask import Flask, request, jsonify
from waitress import serve
import random
import chromadb
from sentence_transformers import SentenceTransformer
import ollama
import sys
import time

# 添加情感状态机工具箱到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'emotion_state_serv'))

from emo_serv import EmotionalStateMachine, generate_reply
from character_card import persona_text

# 设置flask应用
app = Flask(__name__)

# 配置Ollama模型
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_URL = "http://localhost:11434/api/generate"

# 初始化向量数据库（ChromaDB）
chroma_client = chromadb.Client()
memory_collection = chroma_client.get_or_create_collection(name="chat_memory")
# 设置记忆过期时间（以秒为单位，这里是30天）
MEMORY_EXPIRY_TIME = 30 * 24 * 60 * 60  # 30天

class Memory:
    def __init__(self, memory_id, content, timestamp, state):
        self.memory_id = memory_id
        self.content = content
        self.timestamp = timestamp
        self.state = state

    def is_expired(self):
        return time.time() - self.timestamp > MEMORY_EXPIRY_TIME
# 记忆管理器
class MemoryManager:
    def __init__(self, collection, embedding_model):
        self.collection = collection
        self.embedding_model = embedding_model
    
    def add_memory(self, user_msg, assistant_msg, state):
        """添加聊天记忆到向量数据库"""
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

    def retrieve_relevant_memories(self, query, n_results=3):
        """检索与当前查询相关的记忆"""
        query_embedding = self.embedding_model.encode(query).tolist()
        results = self.collection.query(query_embeddings=[query_embedding], n_results=n_results)
        return results
    
    def check_memory_relevance(self, memory, current_state):
        """
        检查记忆是否仍然相关。基于情感状态和优先级进行过滤。
        """
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
        """
        定期清理不相关或过期的记忆。
        """
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

# 全局情感状态机实例
emotional_machine = EmotionalStateMachine()

# 尝试使用本地模型或替代方案
try:
    # 首先尝试使用本地模型路径
    local_model_path = './models/bge-small-zh-v1.5/ai-modelscope/bge-small-zh-v1___5'
    if os.path.exists(local_model_path):
        embedding_model = SentenceTransformer(local_model_path)
        print(f"使用本地模型: {local_model_path}")
    else:
        # 尝试使用中文优化的小模型
        embedding_model = SentenceTransformer('shibing624/text2vec-base-chinese')
        print("使用中文文本向量化模型")
except Exception as e:
    print(f"模型加载失败 {e}, 使用简化的向量化方案")
    # 降级方案：使用简单的关键词匹配
    embedding_model = None

memory_manager = MemoryManager(memory_collection, embedding_model)
def summarize_conversation(user_msg, assistant_msg, current_state):
    """
    使用 LLM 总结对话并生成情感摘要
    """
    prompt = f"""
    用户与智子的对话总结：\n
    用户: {user_msg}\n
    智子: {assistant_msg}\n
    当前情感状态: {current_state}\n
    请总结这段对话，提取出用户的情感波动、智子的反应，并用简短的语言总结这段对话。
    """

    try:
        response = ollama.generate(
            model="mistral:latest",
            prompt=prompt,
            stream=False
        )
        return response["response"]
    except Exception as e:
        print(f"调用Ollama失败: {e}")
        return "对话总结失败，请稍后再试。"
def get_ollama_response(prompt):
    """调用本地 Ollama 模型获取响应"""
    try:
        response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt, stream=False)
        return response["response"]
    except Exception as e:
        print(f"Ollama 调用失败: {e}")
        return "抱歉，我现在有点忙，稍后再聊吧～"

def generate_chat_prompt(user_msg, state):
    """生成带有角色设定和当前状态的聊天提示"""
    persona = persona_text()
    state_info = emotional_machine.get_state_description(state)
    
    relevant_memories = memory_manager.retrieve_relevant_memories(user_msg)
    
    memory_context = ""
    if relevant_memories and relevant_memories['documents']:
        memory_context = "【以下是与当前对话相关的历史记忆】\n"
        for memory in relevant_memories['documents'][0]:
            memory_context += f"{memory}\n"

    prompt = f"""
    {persona}
    
    【当前状态：{state}】
    {state_info}
    
    {memory_context}
    
    【当前对话】
    用户：{user_msg}
    智子："""
    
    return prompt

@app.route("/chat", methods=["POST"])
def chat():
    """处理聊天请求"""
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        
        if not user_msg:
            return jsonify({"error": "缺少message参数"}), 400
        
        # 更新情感状态
        new_state = emotional_machine.determine_state(user_msg)
        
        # 生成带有角色设定和状态的提示
        prompt = generate_chat_prompt(user_msg, new_state)
        
        # 调用 Ollama 获取回复
        ollama_response = get_ollama_response(prompt)
        print(f"Ollama 回复: {ollama_response}")
        # 存储聊天记忆（简化版本，减少LLM调用）
        memory_manager.add_memory(user_msg, ollama_response, new_state)
        
        # 定期清理改为异步或降低频率
        # memory_manager.clean_up_memory()  # 注释掉或改为定时任务
        
        # 返回完整回复
        return jsonify({
            "response": ollama_response,
            "current_state": new_state,
            "state_description": emotional_machine.get_state_description(new_state),
            "emotional_variables": emotional_machine.variables
        })
        
    except Exception as e:
        print(f"聊天服务错误: {e}")
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500

    

@app.route("/mcp/chat", methods=["POST"])
def mcp_chat():
    """MCP协议兼容的聊天接口"""
    try:
        data = request.get_json()
        
        if not data or "method" not in data:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Invalid JSON-RPC request"},
                "id": None
            }), 400
        
        method = data["method"]
        params = data.get("params", {})
        request_id = data.get("id")
        
        if method == "chat":
            user_msg = params.get("message", "")
            
            if not user_msg:
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "缺少message参数"},
                    "id": request_id
                }), 400
            
            # 更新情感状态
            new_state = emotional_machine.determine_state(user_msg)
            
            # 生成带有角色设定和状态的提示
            prompt = generate_chat_prompt(user_msg, new_state)
            
            # 调用 Ollama 获取回复
            ollama_response = get_ollama_response(prompt)
            
            # 存储聊天记忆
            summary = summarize_conversation(user_msg, ollama_response, new_state)
            memory_manager.add_memory(user_msg, summary, new_state)
            
            return jsonify({
                "jsonrpc": "2.0",
                "result": {
                    "response": ollama_response,
                    "state": new_state,
                    "state_description": emotional_machine.get_state_description(new_state),
                    "variables": emotional_machine.variables
                },
                "id": request_id
            })
        
        else:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": request_id
            }), 404
            
    except Exception as e:
        print(f"MCP聊天服务错误: {e}")
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            "id": None
        }), 500

@app.route("/health", methods=["GET"])
def health_check():
    """健康检查接口"""
    return jsonify({"status": "ok", "service": "Ollama Chat Service with Emotion State Machine"})

if __name__ == "__main__":
    print("Ollama聊天服务已启动，端口 9602")
    print("支持的接口:")
    print("  - POST /chat: 简单聊天接口")
    print("  - POST /mcp/chat: MCP协议兼容的聊天接口")
    print("  - GET /health: 健康检查")
    print(f"  - 使用模型: {OLLAMA_MODEL}")
    print("  - 情感状态机已集成")
    serve(app, host="0.0.0.0", port=9602)