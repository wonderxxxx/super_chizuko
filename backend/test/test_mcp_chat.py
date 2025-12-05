import requests

# 测试MCP聊天接口
def test_mcp_chat():
    url = "http://localhost:9602/mcp/chat"
    # 使用正确的JSON-RPC格式
    data = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {
            "message": "在干嘛"
        },
        "id": 1
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    test_mcp_chat()