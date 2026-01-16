"""
全流程任务仿真主程序 (run_full_mission.py)

功能描述:
    该脚本模拟了一个完整的无人机集群任务流程，包含以下四个阶段：
    1. 图像理解与区域划分: 上传战场照片，利用多模态大模型(Gemini)识别区域并生成JSON数据。
    2. 任务指令生成: 基于区域数据，生成无人机搜索任务的Python控制指令。
    3. 任务与搜索执行: 执行搜索指令，并修正无人机坐标以准备后续模拟。
    4. 突发事件响应: 模拟火情，检索引擎中的可用技能，生成并执行应急灭火指令。

主要依赖:
    - google.genai: Google Gemini 大模型 SDK
    - data: 包含无人机原子技能库 (SearchArea, FlyToPoint 等)
"""

import json
import os
import inspect
import glob
from google import genai
from google.genai import types

import data.function as function
from data.prompts import task_prompt_json2
from tools.generate_commands import create_command_prompt
from tools.visualization import visualize_segmentation_on_image


# 从同目录下的 Key.txt 读取 API Key
base_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(base_dir, "Key.txt")

with open(key_path, "r", encoding="utf-8-sig") as f:
    api_key = f.read().strip()

if not api_key:
    raise ValueError(f"Key.txt 为空或未读取到 api_key: {key_path}")

client = genai.Client(api_key=api_key)

#控制大模型自由度为0.
config = types.GenerateContentConfig(temperature=0.0)

# ==========================================
# 全局状态 (State)
# ==========================================
uav_positions = {}
uav_extinguishers = {}

# ==========================================
# 辅助函数: 安全执行 Python 代码
# ==========================================
def execute_generated_code(code_str, stage_name):
    print(f"\n>>> [{stage_name}] 正在执行指令...")
    
    clean_code = code_str.replace("```python", "").replace("```", "").strip()
    
    # 注入上下文
    local_scope = {}
    
    # 动态获取 data 模块中的所有函数 (SearchArea, FlyToPoint, DropFireExtinguisher, GetAllUAVStatus 等)
    execution_context = {}
    for name, obj in inspect.getmembers(function):
        if inspect.isfunction(obj) and not name.startswith("_"):
            execution_context[name] = obj

    try:
        # 完全模仿 test_mission_execution.py 的写法，不传入 globals()
        exec(clean_code, execution_context)
        print(f">>> [{stage_name}] 执行完毕。")
        return execution_context.get('zones_config', None) 
    except Exception as e:
        print(f"[ERROR] {stage_name} 执行出错: {e}")
        return None

# ==========================================
# 辅助函数: 打印输入输出分隔符
# ==========================================
def log_section(title):
    print(f"\n{'='*50}")
    print(f"【{title}】")
    print(f"{'='*50}")

def log_io(label, content):
    print(f"\n--- {label} ---")
    print(content)
    print("--------------------------------------------------")

# ==========================================
# 1. 图像理解与区域划分(检查完毕)
# ==========================================
def phase_1_image_analysis(image_path):
    log_section("PHASE 1: 图像理解与区域划分 (Image Analysis)")
    
    # 上传图片
    my_file = client.files.upload(file=image_path)
    
    task_prompt = task_prompt_json2
    
    # log_io("Input Prompt (输入提示词)", task_prompt)
    
    response = client.models.generate_content(
        model="gemini-3-pro-preview",
        contents=[my_file, task_prompt],
        config=config
    )
    
    # log_io("Model Output (大模型输出)", response.text)
    
    # 解析 JSON 数据
    # print(">>> 正在解析 JSON 数据...")
    try:
        raw_text = response.text.strip()
        # 清理可能存在的 markdown 标记
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.replace("```", "").strip()
            
        zones_data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        zones_data = []

    if zones_data:
        # print(f"成功提取区域数据，共 {len(zones_data)} 个区域。")
        # print(zones_data)
        return zones_data
    else:
        print("Critical Error: 无法获取区域划分数据。")
        return []

# ==========================================
# 2. 任务指令生成（检查完成）
# ==========================================
def phase_2_mission_planning(zones_data):
    log_section("PHASE 2: 任务规划 (Mission Planning)")
    
    if not zones_data:
        print("无区域数据，跳过此步骤。")
        return ""
        
    # print("正在构建任务提示词...")
    prompt = create_command_prompt(zones_data)
    
    # log_io("Input Prompt (输入提示词 - 这里是完整的Prompt内容)", prompt)
    
    # print(">>> 正在请求大模型生成搜索指令...")
    response = client.models.generate_content(
        model="gemini-3-pro-preview",
        contents=[prompt],
        config=config
    )
    
    # log_io("Model Output (大模型输出指令)", response.text)
    return response.text

# ==========================================
# 主程序
# ==========================================
if __name__ == "__main__":
    
    # --- 配置区域 ---
    image_dir = "temp"                        # 图片文件夹路径
    zones_output_file = "all_zones_data.json"      # 结果存储路径 1
    missions_output_file = "all_missions_code.json" # 结果存储路径 2
    
    proxy_port = "7897" 
    proxy_url = f"http://127.0.0.1:{proxy_port}"

    # --- 环境配置 ---
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    print(f"✅ 代理已配置，正在连接端口: {proxy_port}")

    # --- 初始化数据容器 ---
    # 使用字典结构，以文件名作为 key，方便后续索引
    all_zones_record = {}     
    all_missions_record = {}  

    # 获取文件夹下所有图片 (支持 jpg, png, jpeg)
    image_extensions = ['*.jpg', '*.jpeg', '*.png']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(image_dir, ext)))
    
    print(f"📂 扫描到 {len(image_files)} 张图片，准备开始批量处理...")

    # --- 批量循环处理 ---
    for index, image_path in enumerate(image_files):
        file_name = os.path.basename(image_path) # 获取文件名，如 "6.jpg"
        print(f"\n--- [{index+1}/{len(image_files)}] 正在处理: {file_name} ---")
        
        try:
            # Step 1: Image -> JSON
            print("⏳ 执行 Phase 1: 图像分析...")
            zones = phase_1_image_analysis(image_path)
            
            if zones:
                # 收集 Zones 数据
                all_zones_record[file_name] = zones
                
                # 可视化 (保留原有容错逻辑)
                try:
                    visualize_segmentation_on_image(str(zones), image_path)
                except Exception as e:
                    print(f"⚠️ {file_name} 可视化跳过: {e}")

                # Step 2: JSON -> Plan
                print("⏳ 执行 Phase 2: 任务规划...")
                mission_code = phase_2_mission_planning(zones)
                
                # 收集 Mission Code 数据
                if mission_code:
                    all_missions_record[file_name] = mission_code
                else:
                    print(f"⚠️ {file_name} Phase 2 返回为空")
                    all_missions_record[file_name] = None
            else:
                print(f"❌ {file_name} Phase 1 失败 (无 zones 数据)")
                all_zones_record[file_name] = None
                
        except Exception as e:
            print(f"❌ 处理 {file_name} 时发生严重错误: {e}")

    # --- 结果存储 ---
    print("\n💾 正在保存结果文件...")

    # 保存 Zones
    try:
        with open(zones_output_file, 'w', encoding='utf-8') as f:
            json.dump(all_zones_record, f, ensure_ascii=False, indent=4)
        print(f"✅ Zones 数据已保存至: {zones_output_file}")
    except Exception as e:
        print(f"❌ 保存 Zones 文件失败: {e}")

    # 保存 Mission Codes
    try:
        with open(missions_output_file, 'w', encoding='utf-8') as f:
            json.dump(all_missions_record, f, ensure_ascii=False, indent=4)
        print(f"✅ Mission Codes 已保存至: {missions_output_file}")
    except Exception as e:
        print(f"❌ 保存 Mission 文件失败: {e}")

    print("\n🎉 全流程批量任务结束。")