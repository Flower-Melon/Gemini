"""
初始化gemini.Client 对象的工具函数
包括读取api key 和 配置代理（默认7897端口，挂梯子使用）
"""
import os
from google import genai

def setup_client():
    """读取 API Key 并配置代理，返回 Client 对象"""
    # 1. 读取 API Key - 从项目根目录查找 key.txt（不区分大小写）
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 尝试多个可能的文件名
    key_paths = [
        os.path.join(base_dir, "key.txt"),
        os.path.join(base_dir, "Key.txt"),
        os.path.join(os.path.dirname(base_dir), "key.txt"),
    ]
    
    key_path = None
    for path in key_paths:
        if os.path.exists(path):
            key_path = path
            break
    
    if not key_path:
        raise FileNotFoundError(f"未找到 API Key 文件。请确保 key.txt 在项目根目录。尝试的路径: {key_paths}")

    with open(key_path, "r", encoding="utf-8-sig") as f:
        api_key = f.read().strip()
    
    # 2. 配置代理
    proxy_port = "7897"
    proxy_url = f"http://127.0.0.1:{proxy_port}"
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    
    print(f"✅ [System] 客户端已初始化 (Proxy: {proxy_port})")
    return genai.Client(api_key=api_key)