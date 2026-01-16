import os
from google import genai

def setup_client():
    """读取 Key 并配置代理，返回 Client 对象"""
    # 1. 读取 API Key
    base_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(base_dir, "Key.txt")
    
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"未找到 Key.txt: {key_path}")

    with open(key_path, "r", encoding="utf-8-sig") as f:
        api_key = f.read().strip()
    
    # 2. 配置代理
    proxy_port = "7897"
    proxy_url = f"http://127.0.0.1:{proxy_port}"
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    
    print(f"✅ [System] 客户端已初始化 (Proxy: {proxy_port})")
    return genai.Client(api_key=api_key)