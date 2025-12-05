import os
import ollama
from sentence_transformers import SentenceTransformer
from config import Config

class AIManager:
    """AI模型管理器"""
    
    def __init__(self):
        self.ollama_model = Config.OLLAMA_MODEL
        self.embedding_model = self._load_embedding_model()
    
    def _load_embedding_model(self):
        """加载嵌入模型"""
        try:
            # 首先尝试使用本地模型路径
            if os.path.exists(Config.LOCAL_MODEL_PATH):
                embedding_model = SentenceTransformer(Config.LOCAL_MODEL_PATH)
                print(f"使用本地模型: {Config.LOCAL_MODEL_PATH}")
            else:
                # 尝试使用中文优化的小模型
                embedding_model = SentenceTransformer(Config.FALLBACK_MODEL)
                print("使用中文文本向量化模型")
            return embedding_model
        except Exception as e:
            print(f"模型加载失败 {e}, 使用简化的向量化方案")
            # 降级方案：使用简单的关键词匹配
            return None
    
    def get_ollama_response(self, prompt):
        """调用本地 Ollama 模型获取响应"""
        try:
            response = ollama.generate(model=self.ollama_model, prompt=prompt, stream=False)
            ollama_response = response["response"]
            
            # 清理多余的空格和换行符
            cleaned_response = ollama_response.replace('\n', '').replace('\r', '').replace('  ', ' ').strip()
            
            # 限制回复长度，最多90个可见字符
            max_length = 90
            if len(cleaned_response) > max_length:
                # 在max_length以内查找合适的截断点，避免截断在中间
                truncate_points = ['.', '。', '!', '！', '?', '？', '~', '～', '"', '”', '’']
                # 从max_length-10开始向前查找，确保截断后的回复流畅自然
                for i in range(max_length-1, max_length//2, -1):
                    if cleaned_response[i] in truncate_points:
                        return cleaned_response[:i+1]
                # 如果没有合适的截断点，直接截断
                return cleaned_response[:max_length] + '...'
            
            return cleaned_response
        except Exception as e:
            print(f"Ollama 调用失败: {e}")
            return "抱歉，我现在有点忙，稍后再聊吧～"
    
    def summarize_conversation(self, user_msg, assistant_msg, current_state):
        """使用 LLM 总结对话并生成情感摘要"""
        prompt = f"""
        用户与智子的对话总结：
        
        用户: {user_msg}
        智子: {assistant_msg}
        当前情感状态: {current_state}
        请总结这段对话，提取出用户的情感波动、智子的反应，并用简短的语言总结这段对话。
        """

        try:
            response = ollama.generate(
                model=Config.OLLAMA_MODEL,
                prompt=prompt,
                stream=False
            )
            return response["response"]
        except Exception as e:
            print(f"调用Ollama失败: {e}")
            return "对话总结失败，请稍后再试。"
