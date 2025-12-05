from flask import request, jsonify
from config import Config
from database import get_db, get_or_create_user, get_or_create_memory_collection

class ChatService:
    """聊天服务类"""
    
    def __init__(self, emotional_machine, memory_manager, ai_manager, prompt_generator, chroma_client):
        self.emotional_machine = emotional_machine
        self.memory_manager = memory_manager
        self.ai_manager = ai_manager
        self.prompt_generator = prompt_generator
        self.chroma_client = chroma_client
    
    def register_routes(self, app):
        """注册路由"""
        # 直接在应用上注册路由，不使用蓝图
        @app.route("/chat", methods=["POST"])
        def chat():
            """
            处理聊天请求
            """
            return self._handle_chat_request()
        
        @app.route("/mcp/chat", methods=["POST"])
        def mcp_chat():
            """
            MCP协议兼容的聊天接口
            """
            return self._handle_mcp_chat_request()
        
        @app.route("/health", methods=["GET"])
        def health_check():
            """
            健康检查接口
            """
            return self._health_check()
    
    def _handle_user_identity(self, data):
        """处理用户身份，获取或创建用户及其记忆集合"""
        # 获取用户邮箱
        email = data.get("email", "default@example.com")
        
        # 获取数据库会话
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # 获取或创建用户
            user = get_or_create_user(db, email)
            print(f"用户: {user.email}, ID: {user.id}")
            
            # 获取或创建用户的记忆集合
            memory_collection = get_or_create_memory_collection(db, user.id, user.email)
            print(f"记忆集合: {memory_collection.collection_name}")
            
            # 设置当前记忆管理器使用的集合
            self.memory_manager.set_collection_by_name(memory_collection.collection_name)
            
            return user, memory_collection
        finally:
            # 关闭数据库会话
            next(db_gen, None)
    
    def _handle_chat_request(self):
        """处理聊天请求的内部方法"""
        try:
            data = request.get_json()
            user_msg = data.get("message", "")
            
            if not user_msg:
                return jsonify({"error": "缺少message参数"}), 400
            
            # 处理用户身份，获取或创建用户及其记忆集合
            self._handle_user_identity(data)
            
            # 更新情感状态
            new_state = self.emotional_machine.determine_state(user_msg)
            
            # 生成带有角色设定和状态的提示
            prompt = self.prompt_generator.generate_chat_prompt(user_msg, new_state)
            
            # 调用 Ollama 获取回复
            ollama_response = self.ai_manager.get_ollama_response(prompt)
            print(f"Ollama 回复: {ollama_response}")
            
            # 存储聊天记忆
            self.memory_manager.add_memory(user_msg, ollama_response, new_state)
            
            # 返回完整回复
            return jsonify({
                "response": ollama_response,
                "current_state": new_state,
                "state_description": self.emotional_machine.get_state_description(new_state),
                "emotional_variables": self.emotional_machine.variables
            })
            
        except Exception as e:
            print(f"聊天服务错误: {e}")
            return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500
    
    def _handle_mcp_chat_request(self):
        """处理MCP聊天请求的内部方法"""
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
                
                # 处理用户身份，获取或创建用户及其记忆集合
                self._handle_user_identity(params)
                
                # 更新情感状态
                new_state = self.emotional_machine.determine_state(user_msg)
                
                # 生成带有角色设定和状态的提示
                prompt = self.prompt_generator.generate_chat_prompt(user_msg, new_state)
                
                # 调用 Ollama 获取回复
                ollama_response = self.ai_manager.get_ollama_response(prompt)
                
                # 存储聊天记忆
                summary = self.ai_manager.summarize_conversation(user_msg, ollama_response, new_state)
                self.memory_manager.add_memory(user_msg, summary, new_state)
                
                return jsonify({
                    "jsonrpc": "2.0",
                    "result": {
                        "response": ollama_response,
                        "state": new_state,
                        "state_description": self.emotional_machine.get_state_description(new_state),
                        "variables": self.emotional_machine.variables
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
    
    def _health_check(self):
        """健康检查"""
        return jsonify({"status": "ok", "service": "Ollama Chat Service with Emotion State Machine"})
