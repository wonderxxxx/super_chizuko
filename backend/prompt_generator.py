import sys
import os

# 确保能正确导入情感状态机模块
if not os.path.abspath(os.path.join(os.path.dirname(__file__), 'emotion_state_serv')) in sys.path:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'emotion_state_serv')))

from character_card import persona_text
from config import Config

class PromptGenerator:
    """提示词生成器"""
    
    def __init__(self, emotional_machine, memory_manager):
        self.emotional_machine = emotional_machine
        self.memory_manager = memory_manager
    
    def generate_chat_prompt(self, user_msg, state):
        """生成带有角色设定和当前状态的聊天提示"""
        full_persona = persona_text()
        state_info = self.emotional_machine.get_state_description(state)
        
        # 根据当前状态过滤角色设定内容
        filtered_persona = full_persona
        
        # 在学者模式下，过滤掉与机甲/蜂黄泉相关的内容
        if state in ['S2', 'explain']:
            filtered_persona = full_persona.replace('- 对限定玩具 / 机甲极度狂热，尤其是「蜂黄泉」。', '')
            filtered_persona = filtered_persona.replace('- 为了买限定玩具会忍辱点儿童套餐并喊羞耻台词。', '')
            filtered_persona = filtered_persona.replace('S5：宅女模式（机甲狂热）\n    - 听到机甲 / 蜂黄泉 / 限定玩具立刻兴奋。\n    - 强行安利模型给用户。', '')
            filtered_persona = filtered_persona.replace('② 学者面：成熟、专业、冷静、逻辑严密。\n    - 工作模式下像一位经验老练的研究员。\n    - 能清晰解释复杂物理、AI、量子理论。\n    - 做过大量高强度计算，偶尔会「脑袋过热」。', '② 学者面：成熟、专业、冷静、逻辑严密。\n    - 工作模式下像一位经验老练的研究员。\n    - 能清晰解释复杂物理、AI、量子理论。\n    - 做过大量高强度计算，偶尔会「脑袋过热」。\n    - 专注于学术问题，不会提及与学术无关的个人爱好。')
        
        relevant_memories = self.memory_manager.retrieve_relevant_memories(user_msg)
        
        memory_context = ""
        if relevant_memories and relevant_memories['documents']:
            memory_context = "【以下是与当前对话相关的历史记忆】\n"
            for memory in relevant_memories['documents'][0]:
                memory_context += f"{memory}\n"

        prompt = f"""
        {filtered_persona}
        
        【当前状态：{state}】
        {state_info}
        
        {memory_context}
        
        【当前对话】
        用户：{user_msg}
        【回复要求】
        1. 保持智子的角色设定和当前状态
        2. 回复简洁明了，控制在2-3句话，不要超过100字
        3. 语言风格符合妹妹的身份，自然亲切
        4. 避免冗长的解释和复杂的句式
        智子："""
        
        return prompt
