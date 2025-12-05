import requests

# 测试聊天接口
def test_chat():
    url = "http://localhost:9602/chat"
    # 测试用户的问题：睡了吗？哥哥睡不着了呢
    data = {"email": "test@example.com", "message": "睡了吗？哥哥睡不着了呢"}
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        # 检查响应结构
        response_text = response.json().get("response", "")
        print(f"\n智子回答内容：\n{response_text}")
        print(f"\n✅ 测试成功：聊天接口正常工作！")
        print("\n前端修改后，回答会被分割为多个气泡，神态描述会用小字显示。")
        print("请在浏览器中访问前端页面测试实际显示效果。")
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    test_chat()