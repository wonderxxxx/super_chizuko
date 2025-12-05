from transformers import AutoModel, AutoTokenizer

model_path = './models/bge-small-zh-v1.5/ai-modelscope/bge-small-zh-v1___5'

# 确保模型目录下有 config.json
try:
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModel.from_pretrained(model_path)
    print("模型加载成功")
except Exception as e:
    print(f"模型加载失败: {e}")
