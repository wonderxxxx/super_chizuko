# backend/prompt_builder.py
"""
Prompt Builder — unify all system prompts, chat prompts, memory injection,
emotion state, and character card.

This module is designed to work with:
- memory_manager_wrapper.py
- emotion_state_serv/
- prompt_generator.py (old version, can be replaced)
- ai_manager.py
"""

from typing import List, Optional, Dict

class PromptBuilder:
    """
    Build complete prompts for your LLM, including:
    - System base prompt (character card)
    - Emotion state
    - Memory context
    - User message
    - Conversation history
    """

    def __init__(
        self,
        character_card: Optional[str] = None,
        memory_mgr=None,
        emotion_serv=None,
        max_history: int = 8,
    ):
        self.character_card = character_card
        self.memory_mgr = memory_mgr
        self.emotion_serv = emotion_serv
        self.max_history = max_history

    # =========================
    #  System Prompt
    # =========================
    def build_system_prompt(self) -> str:
        """
        Provide a stable character identity.
        If character_card is None, load default one.
        """
        if self.character_card:
            return self.character_card

        # 默认角色：智子妹妹人格
        return (
            "你是一位名叫「智子」的妹妹，聪明、温柔、贴心，语气自然、亲昵。"
            "你的任务是陪伴、解释问题、安抚情绪，不使用机械化语气。"
        )

    # =========================
    #  Memory
    # =========================
    def build_memory_context(self, user_query: str) -> str:
        """
        Inject memory retrieved from memory_manager_v2 / wrapper.
        """
        if not self.memory_mgr:
            return ""

        try:
            memories = self.memory_mgr.retrieve(user_query)
        except Exception:
            memories = []

        if not memories:
            return ""

        memory_text = "\n".join(f"- {m}" for m in memories)
        return f"【相关记忆】\n{memory_text}\n"

    # =========================
    #  Emotion State
    # =========================
    def build_emotion_prompt(self) -> str:
        """
        Pull emotion state from emotion module (character_card.py + emo_serv).
        """
        if not self.emotion_serv:
            return ""

        state = self.emotion_serv.get_state()
        if not state:
            return ""
        
        return f"【情绪状态】\n当前角色情绪为：{state}\n"

    # =========================
    #  Conversation History
    # =========================
    def build_history_prompt(self, history: List[Dict]) -> str:
        """
        Convert conversation history to a compact format.
        """
        if not history:
            return ""

        useful_history = history[-self.max_history:]

        s = "【最近对话】\n"
        for turn in useful_history:
            role = "你" if turn["role"] == "user" else "智子"
            s += f"{role}：{turn['content']}\n"

        return s

    # =========================
    # Final Builder
    # =========================
    def build_prompt(
        self,
        user_query: str,
        history: List[Dict] = None,
    ) -> str:
        """
        Build the final prompt sent to the model.
        """

        system_prompt = self.build_system_prompt()
        memory_prompt = self.build_memory_context(user_query)
        emotion_prompt = self.build_emotion_prompt()
        history_prompt = self.build_history_prompt(history or [])

        final_prompt = (
            f"{system_prompt}\n\n"
            f"{emotion_prompt}"
            f"{memory_prompt}"
            f"{history_prompt}"
            f"【用户消息】\n{user_query}\n\n"
            "请以智子的身份自然地回应。"
        )

        return final_prompt


# ==========================
#  Factory Function
# ==========================
def create_prompt_builder(app_context: dict):
    """
    app_context 示例:
    {
        'memory_mgr': MemoryManagerWrapper(),
        'emotion_serv': EmotionService(),
        'character_card': "...角色定义..."
    }
    """
    return PromptBuilder(
        character_card=app_context.get("character_card"),
        memory_mgr=app_context.get("memory_mgr"),
        emotion_serv=app_context.get("emotion_serv"),
        max_history=app_context.get("max_history", 8)
    )
