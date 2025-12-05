import os
import sys

# 添加情感状态机工具箱到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'emotion_state_serv'))

class Config:
    """配置类"""
    # Ollama模型配置
    OLLAMA_MODEL = "gemma3:4b"
    OLLAMA_URL = "http://localhost:11434/api/generate"
    
    # 记忆配置
    MEMORY_EXPIRY_TIME = 30 * 24 * 60 * 60  # 30天
    RELEVANT_MEMORIES_COUNT = 3  # 检索相关记忆数量
    
    # Flask应用配置
    FLASK_HOST = "0.0.0.0"
    FLASK_PORT = 9602
    SECRET_KEY = os.urandom(24)  # 用于会话管理
    
    # 模型配置
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LOCAL_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'bge-small-zh-v1.5', 'ai-modelscope', 'bge-small-zh-v1___5')
    FALLBACK_MODEL = 'shibing624/text2vec-base-chinese'
    
    # 情感状态机配置
    EMOTION_STATE_MODULE = "emo_serv"
    CHARACTER_CARD_MODULE = "character_card"
    
    # 数据库配置
    DB_PATH = os.path.join(BASE_DIR, 'data.db')  # SQLite数据库路径
    DATABASE_URL = f'sqlite:///{DB_PATH}'
    
    # Chroma配置
    CHROMA_PERSIST_DIRECTORY = os.path.join(BASE_DIR, 'chroma_db')  # Chroma持久化目录
    
    # Redis配置（可选）
    REDIS_URL = None  # 如果使用Redis，设置为redis://localhost:6379/0

