import os
import glob
import json
from google.genai import types

from tools.utils import setup_client
from tools.visualization import visualize_segmentation_on_image
from data.prompts import system_task_prompt_json, user_task_prompt_json

# 配置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "temp")      # 图片输入文件夹
OUTPUT_DIR = os.path.join(BASE_DIR, "out")    # 结果输出文件夹

# 确保 output 文件夹存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 定义输出文件路径
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "zones_data.json")

class VisionAnalyzer:
    def __init__(self, client):
        """
        初始化视觉分析器
        :param client: 已初始化的 google.genai.Client 实例
        """
        self.client = client
        # 设置生成配置，温度设为0以保证JSON格式稳定
        self.config = types.GenerateContentConfig(
            system_instruction=system_task_prompt_json,
            response_mime_type="application/json",
            temperature=0.0
        )

    def analyze_scene(self, image_path):
        """
        执行 Phase 1: 上传图片并获取区域划分数据 (JSON)
        """
        print(f"   [Vision] 正在上传并分析图像: {image_path}...")
        
        try:
            # 上传图片
            my_file = self.client.files.upload(file=image_path)
            
            # 调用大模型
            response = self.client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=[user_task_prompt_json,my_file],
                config=self.config
            )
            
            return self._parse_json_response(response.text)
            
        except Exception as e:
            print(f"   [Vision Error] 图像分析请求失败: {e}")
            return []

    def _parse_json_response(self, raw_text):
        """内部方法：清理 markdown 标记并解析 JSON"""
        try:
            text = raw_text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            elif text.startswith("```"):
                text = text.replace("```", "").strip()
                
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"   [Vision Error] JSON 解析失败: {e}")
            return []
        
def main():
    # 1. 初始化
    client = setup_client()
    vision_system = VisionAnalyzer(client)
    
    # 2. 扫描图片
    image_extensions = ['*.jpg', '*.jpeg', '*.png']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(IMAGE_DIR, ext)))
    
    print(f"👁️ [Step 1] 开始视觉分析任务，共 {len(image_files)} 张图片")
    
    results = {}

    # 3. 批量处理
    for index, image_path in enumerate(image_files):
        file_name = os.path.basename(image_path)
        print(f"\n--- 处理中 [{index+1}/{len(image_files)}]: {file_name} ---")
        
        # 调用视觉层
        zones = vision_system.analyze_scene(image_path)
        
        if zones:
            print(f"   ✅ 获取到 {len(zones)} 个区域数据")
            results[file_name] = zones
            
            # 可视化 (可选)
            try:
                visualize_segmentation_on_image(str(zones), image_path)
            except Exception as e:
                print(f"   ⚠️ 可视化失败: {e}")
        else:
            print(f"   ❌ 分析失败或无数据")
            results[file_name] = None

    # 4. 保存中间结果
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"\n💾 [Step 1 完成] 区域数据已保存至: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()