import json
import random
import numpy as np

# --- 1. 配置基础资源 ---
DRONES_EXT = ['UAV_01', 'UAV_02', 'UAV_03'] # 灭火无人机
DRONES_SUR = ['UAV_04', 'UAV_05']           # 侦察无人机

RISK_TYPES = {
    "High": ["森林/起伏地形", "密林", "核心火场", "灌木丛"],
    "Low": ["草地/灌木", "稀疏林地", "道路边缘"],
    "Monitor": ["未过火森林", "安全隔离带", "开阔空地"]
}

# 话术模板，增加文本的多样性
REASON_TEMPLATES = {
    "High": [
        "该区域包含明显明火带，火势呈{direction}蔓延，需压制。",
        "检测到{color}浓烟，位于{location}，且紧邻易燃植被。",
        "核心燃烧区，热成像显示极高温度，必须进行定点清除。",
        "火势猛烈且风速较大，有突破隔离带风险，优先级最高。"
    ],
    "Low": [
        "存在零星散落火点，火势较弱但有复燃风险。",
        "位于主火场{location}侧，受烟雾影响，需清理余火。",
        "虽然无明火，但红外显示局部高温，需防止复燃。"
    ],
    "Monitor": [
        "当前无可见明火或烟雾，属于安全背景区域。",
        "位于下风向，主要受烟雾飘散影响，需例行巡逻。",
        "大面积未过火林区，需监控是否有飞火跨越。"
    ]
}

# --- 2. 辅助函数 ---

def generate_polygon():
    """生成一个简单的随机多边形坐标 (模拟0.0-1.0之间)"""
    base_x = random.uniform(0, 0.8)
    base_y = random.uniform(0, 0.8)
    # 生成3-5个点
    points = []
    for _ in range(random.randint(3, 5)):
        px = min(1.0, max(0.0, base_x + random.uniform(0, 0.3)))
        py = min(1.0, max(0.0, base_y + random.uniform(0, 0.3)))
        points.append([round(px, 2), round(py, 2)])
    return points

def generate_reason(risk_level):
    """根据风险等级生成逼真的描述"""
    template = random.choice(REASON_TEMPLATES[risk_level])
    return template.format(
        direction=random.choice(["向东", "向北", "向西南", "四周"]),
        color=random.choice(["黑色", "橙色", "灰白色"]),
        location=random.choice(["左侧", "右下角", "中心", "北部边缘"])
    )

def solve_allocation(zones):
    """
    【硬逻辑核心】
    模拟专家的分配逻辑：
    1. 找出所有 High 区域，优先分配 UAV_01-03
    2. 找出 Low/Monitor 区域，分配剩余飞机或 UAV_04-05
    """
    available_ext = DRONES_EXT.copy()
    available_sur = DRONES_SUR.copy()
    
    missions = []
    
    # 按风险排序：High -> Low -> Monitor
    sorted_zones = sorted(zones, key=lambda x: {"High": 0, "Low": 1, "Monitor": 2}[x['risk_level']])
    
    for zone in sorted_zones:
        assigned_drones = []
        
        if zone['risk_level'] == 'High':
            # 策略：高危区至少分1架灭火机，如果资源够且是大火场，分2架
            if available_ext:
                # 拿走第一架
                assigned_drones.append(available_ext.pop(0))
                # 30%概率且还有飞机，再拿一架（模拟双机编队）
                if available_ext and random.random() < 0.3:
                     assigned_drones.append(available_ext.pop(0))
            else:
                # 没灭火机了？如果还有侦察机，勉强派去盯着（模拟资源耗尽的降级处理）
                if available_sur:
                    assigned_drones.append(available_sur.pop(0))
                    
        else: # Low or Monitor
            # 策略：优先用侦察机，侦察机没了用剩下的灭火机
            if available_sur:
                assigned_drones.append(available_sur.pop(0))
            elif available_ext:
                assigned_drones.append(available_ext.pop(0))
        
        # 如果没分到飞机（资源极度紧缺），则跳过或记录空任务（这里选择不生成指令）
        if assigned_drones:
            # 生成 Python 代码字符串
            code_line = f"SearchArea({str(assigned_drones)}, {str(zone['coordinates'])})"
            missions.append(code_line)
            
    return "\n".join(missions)

# --- 3. 主生成循环 ---

def generate_dataset(num_samples=500):
    dataset = []
    
    for i in range(num_samples):
        # 1. 生成 Zone Data (Input)
        num_zones = random.randint(3, 5) # 每张图3-5个区域
        zones = []
        
        # 确保至少有一个 High，避免数据太无聊
        risk_pool = ['High'] + [random.choice(['High', 'Low', 'Monitor']) for _ in range(num_zones - 1)]
        random.shuffle(risk_pool)
        
        for j, risk in enumerate(risk_pool):
            zone = {
                "id": f"zone_{j}",
                "name": f"Area_{j}_{risk}",
                "risk_level": risk,
                "type": random.choice(RISK_TYPES[risk]),
                "coordinates": generate_polygon(),
                "reason": generate_reason(risk),
                "boundary_description": "自动生成边界描述...",
                "coverage_check": "自动生成覆盖检查..."
            }
            zones.append(zone)
            
        # 2. 生成 Mission Code (Output)
        mission_code = solve_allocation(zones)
        
        # 3. 封装成 Instruction Tuning 格式
        # 加入 System Prompt 强化角色
        entry = {
            "messages": [
                {
                    "role": "system", 
                    "content": "你是一个森林消防无人机指挥AI。请根据区域的 risk_level 和 reason 分配无人机。\n规则：\n1. High Risk 必须优先分配灭火无人机(UAV_01, UAV_02, UAV_03)。\n2. Monitor/Low Risk 分配侦察无人机(UAV_04, UAV_05)。\n3. 输出 Python 函数 SearchArea(drone_list, coordinates)。"
                },
                {
                    "role": "user", 
                    "content": json.dumps(zones, ensure_ascii=False, indent=2)
                },
                {
                    "role": "assistant", 
                    "content": mission_code
                }
            ]
        }
        dataset.append(entry)
    
    return dataset

# --- 4. 执行并保存 ---
if __name__ == "__main__":
    data = generate_dataset(5)
    
    # 保存为 JSONL 文件 (Llama 3 微调标准格式)
    with open("drone_finetune_data.jsonl", "w", encoding="utf-8") as f:
        for entry in data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"成功生成 {len(data)} 条数据，已保存至 drone_finetune_data.jsonl")
    # 打印一条预览
    print("\n--- 样本预览 ---")
    print(data[0]['messages'][2]['content'])