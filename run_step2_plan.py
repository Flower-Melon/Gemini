import os
import json
from google.genai import types

from tools.utils import setup_client
from tools.generate import create_command_prompt

# 配置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "out")

# 定义输入和输出路径
INPUT_JSON = os.path.join(OUTPUT_DIR, "zones_data.json")
OUTPUT_CODE_JSON = os.path.join(OUTPUT_DIR, "missions_plan.json")

class MissionPlanner:
    def __init__(self, client):
        """
        初始化任务规划器
        :param client: 已初始化的 google.genai.Client 实例
        """
        self.client = client
        self.config = types.GenerateContentConfig(temperature=0.0)

    def generate_mission_code(self, zones_data):
        """
        执行 Phase 2: 基于区域数据生成无人机控制代码
        """
        if not zones_data:
            print("   [Planner Warning] 接收到的区域数据为空，跳过规划。")
            return ""

        print("   [Planner] 正在根据区域数据生成任务指令...")

        # 构建指令 Prompt
        prompt = create_command_prompt(zones_data)
        
        try:
            # 大模型生成任务指令
            response = self.client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=[prompt],
                config=self.config
            )
            return response.text
            
        except Exception as e:
            print(f"   [Planner Error] 任务生成请求失败: {e}")
            return ""

def main():
    # 1. 检查输入文件是否存在
    if not os.path.exists(INPUT_JSON):
        print(f"❌ 错误: 未找到输入文件 {INPUT_JSON}")
        print("请先运行 run_step1_vision.py 生成区域数据。")
        return

    # 2. 初始化
    client = setup_client()
    planner = MissionPlanner(client)
    
    # 3. 读取中间数据
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        all_zones_data = json.load(f)
    
    print(f"🧠 [Step 2] 开始任务规划任务，加载了 {len(all_zones_data)} 条记录")
    
    mission_results = {}

    # 4. 批量处理
    count = 0
    for file_name, zones in all_zones_data.items():
        count += 1
        print(f"\n--- 规划中 [{count}/{len(all_zones_data)}]: 来自 {file_name} 的数据 ---")
        
        if not zones:
            print("   ⚠️ 跳过: 对应的区域数据为空")
            mission_results[file_name] = None
            continue
            
        # 调用规划层
        code = planner.generate_mission_code(zones)
        
        if code:
            print("   ✅ 指令生成成功")
            mission_results[file_name] = code
        else:
            print("   ❌ 指令生成失败")
            mission_results[file_name] = None

    # 5. 保存最终结果
    formatted_results = {}
    for key, value in mission_results.items():
        if isinstance(value, str):
            # 去掉可能存在的空行，并按换行符分割
            lines = [line for line in value.split('\n') if line.strip() != '']
            formatted_results[key] = lines
        else:
            formatted_results[key] = value

    with open(OUTPUT_CODE_JSON, 'w', encoding='utf-8') as f:
        json.dump(formatted_results, f, ensure_ascii=False, indent=4)

    print(f"\n💾 [Step 2 完成] 任务代码已保存至: {OUTPUT_CODE_JSON}")

if __name__ == "__main__":
    main()