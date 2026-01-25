"""
动态重规划模块 - 核心功能
用于在任务执行过程中发现新火情时，重新规划无人机任务分配
"""

import json
import os
import sys
from datetime import datetime
from google.genai import types

# 添加父目录到路径，便于导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.utils import setup_client
from tools.generate import get_uav_resources, get_function_definitions
import data.UAV as UAV
import data.function as function


def extract_uavs_in_zone(original_plan, zone_id):
    """
    从原始任务分配计划中提取被分配到特定区域的无人机列表
    
    Args:
        original_plan: 任务分配代码字符串，格式如:
                      SearchArea(['UAV_01', 'UAV_02'], 'zone_east')
                      FlyToFire('UAV_01', [0.5, 0.5])
        zone_id: 区域ID，如 'zone_east'
    
    Returns:
        list: 分配到该区域的无人机ID列表
    """
    import re
    uavs_in_zone = []
    
    # 尝试多种 zone_id 格式
    # 1. SearchArea(['UAV_XX', ...], 'zone_id') 或 SearchArea(['UAV_XX', ...], "zone_id")
    pattern1 = r"SearchArea\(\[([^\]]+)\]\s*,\s*['\"]" + re.escape(zone_id) + r"['\"]"
    matches = re.findall(pattern1, original_plan)
    
    # 2. 如果第一种格式没找到，尝试不用引号的情况
    if not matches:
        pattern2 = r"SearchArea\(\[([^\]]+)\]\s*,\s*" + re.escape(zone_id) + r"(?:[,\)])"
        matches = re.findall(pattern2, original_plan)
    
    for match in matches:
        # 提取中括号内的所有 UAV_XX
        uav_pattern = r"['\"](UAV_\d+)['\"]"
        uavs = re.findall(uav_pattern, match)
        uavs_in_zone.extend(uavs)
    
    # 3. 如果还是没找到，尝试全局搜索包含这个zone_id的行中的无人机
    if not uavs_in_zone:
        pattern3 = r".*" + re.escape(zone_id) + r".*"
        lines_with_zone = re.findall(pattern3, original_plan)
        for line in lines_with_zone:
            uavs = re.findall(r"UAV_\d+", line)
            uavs_in_zone.extend(uavs)
    
    return list(set(uavs_in_zone))  # 去重

# 这里需要维护一个动态的无人机状态列表，
# 就是说，实际应用中，这个状态应该是实时更新的，然后这个函数就可以查询那个实时更新的无人机状态数据
def collect_uav_states(zones_data=None):
    """
    收集无人机状态
    优先从 uav_states.json 文件读取，如果文件不存在则使用默认数据或根据zones_data生成
    
    Args:
        zones_data: 可选的区域数据，用于自动生成无人机状态
    
    Returns:
        list: 无人机状态列表
    """
    # 默认硬编码数据
    return get_default_uav_states()


def get_default_uav_states():
    """
    返回默认的无人机状态（硬编码）
    
    Returns:
        list: 默认无人机状态列表
    """
    return [
        {
            "id": "UAV_01",
            "type": "extinguishing_drone",
            "status": "EXTINGUISHING",
            "assigned_zone": "zone_0",
            "location": [0.695, 0.135],
            "battery": 92.0,
            "capabilities": {
                "max_fire_extinguisher": 2,
                "current_payload": 0,
                "max_speed": 15.0,
                "sensor_range": 0.15
            },
            "description": "正在zone_0扑灭第二个火点，载荷已耗尽，准备返航。"
        },
        {
            "id": "UAV_02",
            "type": "extinguishing_drone",
            "status": "IDLE",
            "assigned_zone": "zone_1",
            "location": [0.308, 0.015],
            "battery": 88.0,
            "capabilities": {
                "max_fire_extinguisher": 2,
                "current_payload": 1,
                "max_speed": 15.0,
                "sensor_range": 0.15
            },
            "description": "已处理完毕，待命中"
        },
        {
            "id": "UAV_03",
            "type": "extinguishing_drone",
            "status": "EXTINGUISHING",
            "assigned_zone": "zone_0",
            "location": [0.905, 0.735],
            "battery": 45.0,
            "capabilities": {
                "max_fire_extinguisher": 2,
                "current_payload": 0,
                "max_speed": 15.0,
                "sensor_range": 0.15
            },
            "description": "负责zone_0核心火区，电量较低，载荷已耗尽。"
        },
        {
            "id": "UAV_04",
            "type": "surveillance_drone",
            "status": "SEARCHING",
            "assigned_zone": "zone_2",
            "location": [0.2, 0.65],
            "battery": 75.0,
            "capabilities": {
                "max_fire_extinguisher": 0,
                "current_payload": 0,
                "max_speed": 25.0,
                "sensor_range": 0.3
            },
            "description": "zone_2安全监控中。"
        },
        {
            "id": "UAV_05",
            "type": "surveillance_drone",
            "status": "SEARCHING",
            "assigned_zone": "zone_0",
            "location": [0.7, 0.5],
            "battery": 95.0,
            "capabilities": {
                "max_fire_extinguisher": 0,
                "current_payload": 0,
                "max_speed": 25.0,
                "sensor_range": 0.3
            },
            "description": "zone_0高空红外侦察支持。"
        }
    ]


def create_replan_prompt(zones_data, original_plan, current_states, new_fires):
    """
    生成重规划提示词
    
    Args:
        zones_data: 原始区域划分数据
        original_plan: 原始任务分配代码
        current_states: 当前无人机状态列表
        new_fires: 新发现的火点列表
    
    Returns:
        str: 格式化的提示词
    """
    
    # 获取函数库
    skills_context = get_function_definitions(function)
    
    # 格式化数据
    zones_json = json.dumps(zones_data, ensure_ascii=False, indent=2)
    states_json = json.dumps(current_states, ensure_ascii=False, indent=2)
    fires_json = json.dumps(new_fires, ensure_ascii=False, indent=2)
    
    prompt = f"""
你是无人机集群指挥官。当前任务执行过程中发现了新的火情，需要重新规划部分无人机的任务。

【1. 技能函数库 (SDK)】
==================================================
{skills_context}

==================================================
【2. 原始区域划分 (zones_data)】
==================================================
{zones_json}

==================================================
【3. 原始任务分配】
==================================================
{original_plan}

==================================================
【4. 当前无人机状态（实时）】
==================================================
{states_json}

==================================================
【5. 新发现的火点】
==================================================
{fires_json}

==================================================
【6. 重规划要求 (CRITICAL)】
==================================================
1. **保留执行中的任务**：
   - 状态为 "busy" 的无人机正在执行任务，除非紧急情况，否则不要中断。
   - 优先调配状态为 "available" 的空闲无人机。

2. **优先处理新火点**：
   - 新发现的火点可能是紧急情况，需要立即派遣无人机。
   - **高风险/极高风险策略**：对于"高"或"极高"风险的新火点，请执行【饱和式救援】——**必须调度所有可用（available）且有灭火弹的无人机**前往支援，不要节省兵力。
   - 优先派遣带灭火弹的无人机（extinguishing_drone）。
   - 如果灭火型无人机都在忙或没有灭火弹了，可以派侦察型（surveillance_drone）先监控。

3. **资源约束考虑**：
   - 检查 `remaining_fire_extinguisher` 字段，已经用完灭火弹的无人机只能做侦察。

4. **输出格式**：
   - 只输出需要**新分配或重新分配**的无人机的指令。
   - 对于保持原任务的无人机，不需要输出指令。
   - 使用 `SearchArea` 或 `FlyToFire` 函数。
   - 直接输出 Python 代码，不要 markdown 标记，不要解释。

==================================================
【8. 生成重规划指令】
==================================================
"""
    return prompt


def execute_replan(zones_data, original_plan, new_fire_event):
    """
    执行重规划流程
    
    Args:
        zones_data: 原始区域划分
        original_plan: 原始任务分配
        new_fire_event: 新火情事件 {"location": [x, y], "estimated_risk": "高", ...}
    
    Returns:
        tuple: (success, replan_code)
    """
    # 初始化客户端
    client = setup_client()
    config = types.GenerateContentConfig(temperature=0.0)
    
    # 创建out文件夹（如果不存在）
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(base_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    
    log_lines = []
    log_lines.append("=" * 60)
    log_lines.append("【动态重规划执行】")
    log_lines.append("=" * 60)
    log_lines.append(f"触发时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_lines.append("")
    
    # 收集当前状态（目前是硬编码）
    current_states = collect_uav_states(zones_data)
    
    # 打印和记录无人机状态
    log_lines.append("【当前无人机实时状态】")
    log_lines.append("-" * 60)
    print("【当前无人机实时状态】")
    for uav in current_states:
        uav_info = f"  {uav['id']}: 类型={uav['type']}, 状态={uav['status']}, 区域={uav['assigned_zone']}, 位置={uav['location']}, 电量={uav['battery']}%"
        print(uav_info)
        log_lines.append(uav_info)
    log_lines.append("-" * 60)
    print("-" * 60)
    log_lines.append("")
    
    # 格式化新火点信息 - 补充必要字段
    new_fires = [{
        "fire_id": new_fire_event.get("fire_id", "new_fire_discovered"),
        "location": new_fire_event.get("location"),
        "estimated_risk": new_fire_event.get("estimated_risk"),
        "discovered_by": new_fire_event.get("discovered_by"),
        "zone_id": new_fire_event.get("zone_id"),
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }]
    
    log_lines.append(f"新火点位置: {new_fires[0]['location']}")
    log_lines.append(f"风险等级: {new_fires[0]['estimated_risk']}")
    log_lines.append(f"发现者: {new_fires[0]['discovered_by']}")
    log_lines.append("")
    
    # 生成重规划提示词并调用大模型
    prompt = create_replan_prompt(zones_data, original_plan, current_states, new_fires)
    
    try:
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=[prompt],
            config=config
        )
        
        # 提取生成的代码
        replan_code = response.text.strip()
        
        # 清理可能的 markdown 标记
        if replan_code.startswith("```python"):
            replan_code = replan_code.replace("```python", "").replace("```", "").strip()
        elif replan_code.startswith("```"):
            replan_code = replan_code.replace("```", "").strip()
        
        log_lines.append("✓ 重规划成功")
        log_lines.append("")
        log_lines.append("生成的重规划指令:")
        log_lines.append("-" * 60)
        log_lines.append(replan_code)
        log_lines.append("-" * 60)
        log_lines.append("")
        
        # 保存日志到文件
        log_content = "\n".join(log_lines)
        log_dir = os.path.join(out_dir, "log")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f"replan_log_{timestamp}.txt")
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)
        print(f"✓ 日志已保存: {log_file}")
        
        return True, replan_code
        
    except Exception as e:
        log_lines.append(f"✗ 重规划失败: {str(e)}")
        log_content = "\n".join(log_lines)
        
        # 保存错误日志到文件
        log_dir = os.path.join(out_dir, "log")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f"replan_log_{timestamp}.txt")
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)
        print(f"✗ 日志已保存: {log_file}")
        
        return False, None

# 这里主要是方便外面调用，按理来说应该是外面传入 zones_data 和 original_plan然后这
# 里就重规划的，但是目前没有想到什么好的办法来解决这个问题。所以现在这
def test_replan():
    """
    测试重规划功能 - 完整的测试流程
    可以从其他模块导入并调用：from tools.replan import test_replan; test_replan()
    """
    # 从 zones_data.json 和 missions_plan.json 读取测试数据
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    zones_json_path = os.path.join(base_dir, "out", "zones_data.json")
    missions_json_path = os.path.join(base_dir, "out", "missions_plan.json")
    
    # 如果 zones_data.json 存在，从文件读取；否则使用默认硬编码数据
    if os.path.exists(zones_json_path):
        print(f"✓ 读取 zones_data.json: {zones_json_path}")
        with open(zones_json_path, 'r', encoding='utf-8') as f:
            all_zones_data = json.load(f)
        
        # 获取第一个图片的区域数据作为测试数据
        # 获取 zones_data.json 中的第一个图片名
        first_file = list(all_zones_data.keys())[0]
        # 使用这个图片名获取对应的区域数据
        test_zones = all_zones_data[first_file]
        print(f"✓ 已加载第一张图片数据: {first_file}")
        
        # 读取对应的任务分配计划
        if os.path.exists(missions_json_path):
            print(f"✓ 读取 missions_plan.json: {missions_json_path}")
            with open(missions_json_path, 'r', encoding='utf-8') as f:
                all_missions_data = json.load(f)
            # 用相同的图片名 first_file 从 missions_plan.json 查找任务分配
            if first_file in all_missions_data and all_missions_data[first_file]:
                mission_lines = all_missions_data[first_file]

                # 获取对应的任务分配计划字符串
                test_original_plan = "\n    ".join(mission_lines) if isinstance(mission_lines, list) else mission_lines
                print(f"✓ 已加载对应的任务分配计划")
            else:
                print(f"⚠️ 未在 missions_plan.json 中找到对应的数据，使用默认计划")               
        else:
            print(f"⚠️ 未找到 missions_plan.json ({missions_json_path})，使用默认计划")        
    else:
        print(f"⚠️ 未找到 zones_data.json ({zones_json_path})，使用默认硬编码数据")

    # 生成新火点事件 - 从监测区（Monitor）中发现新火点
    print("\n>>> 生成新火点事件")
    test_fire_event = None
    
    # 从 test_zones 中查找监测区域（Monitor 区域 - 没有火点的监控区域）
    if isinstance(test_zones, list):
        print(f"✓ zones数据是列表，共 {len(test_zones)} 个区域")
        # 调试：打印所有区域的类型
        for i, zone in enumerate(test_zones):
            risk = zone.get("risk_level", "unknown")
            zone_id = zone.get("id", f"zone_{i}")
            fire_points = zone.get("fire_points", [])
            print(f"  [{i}] {zone_id}: risk_level={risk}, fire_points={len(fire_points) if isinstance(fire_points, list) else 'N/A'}")
        
        monitor_zones = [zone for zone in test_zones 
                        if zone.get("risk_level") == "Monitor" 
                        and not zone.get("fire_points")]
        print(f"  → 找到 {len(monitor_zones)} 个 Monitor 类型的监测区域")
    elif isinstance(test_zones, dict):
        print("✓ zones数据是字典")
        monitor_zones = [test_zones] if (test_zones.get("risk_level") == "Monitor" 
                                         and not test_zones.get("fire_points")) else []
    else:
        print(f"⚠️ zones数据类型未知: {type(test_zones)}")
        monitor_zones = []
    
    if monitor_zones:
        # 从监测区域中选择一个【确保该区域有无人机被分配】
        import random
        valid_zones = []
        
        print(f"  → 检查 {len(monitor_zones)} 个监测区域是否有无人机分配...")
        
        # 筛选出确实有无人机分配的监测区域
        for zone in monitor_zones:
            zone_id = zone.get("id", "")
            print(f"    检查区域: {zone_id}")
            print(f"      原始计划片段: {test_original_plan[:200]}...")  # 调试：看计划内容
            uavs_in_zone = extract_uavs_in_zone(test_original_plan, zone_id)
            print(f"      → 找到无人机: {uavs_in_zone}")
            if uavs_in_zone:
                valid_zones.append((zone, uavs_in_zone))
        
        if not valid_zones:
            print("⚠️ 没有找到有无人机被分配的监测区域，尝试从无火点的区域中生成")
            monitor_zones = []
        else:
            selected_zone, zone_uav_ids = random.choice(valid_zones)
            coordinates = selected_zone.get("coordinates", [])
            
            # 获取该区域被分配的无人机的实时状态
            all_uav_states = collect_uav_states()
            zone_uav_states = [u for u in all_uav_states if u["id"] in zone_uav_ids]
        
        if monitor_zones and coordinates and len(coordinates) >= 2:
            # 计算坐标范围的中心
            coords_array = coordinates if isinstance(coordinates[0], (list, tuple)) else [coordinates]
            xs = [c[0] for c in coords_array]
            ys = [c[1] for c in coords_array]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            # 在监测区域内随机生成新火点
            new_fire_x = round(random.uniform(min_x, max_x), 3)
            new_fire_y = round(random.uniform(min_y, max_y), 3)
            new_fire_location = [new_fire_x, new_fire_y]
            
            # 从该区域被分配的无人机中选择发现者
            # 优先选择侦察型无人机（surveillance_drone）
            surveillance_in_zone = [u for u in zone_uav_states if u["type"] == "surveillance_drone"]
            random_uav = random.choice(surveillance_in_zone) if surveillance_in_zone else random.choice(zone_uav_states)
            
            test_fire_event = {
                "location": new_fire_location,
                "estimated_risk": "高",  # 新发现的火点默认标记为"高"风险
                "discovered_by": random_uav["id"],
                "zone_id": selected_zone.get("id", "unknown_zone"),
                "description": f"在监测区 '{selected_zone.get('id')}' 中新发现火情"
            }
            print(f"✓ 在监测区 '{selected_zone.get('id')}' 中发现新火点: {new_fire_location}")
            print(f"✓ 发现者: {random_uav['id']} ({random_uav['type']})")
    else:
        print("⚠️ 未找到监测区域，尝试从无火点的区域中生成")
        # 降级：从没有火点的任何区域中生成
        if isinstance(test_zones, list):
            no_fire_zones = [zone for zone in test_zones 
                            if not zone.get("fire_points")]
        elif isinstance(test_zones, dict):
            no_fire_zones = [test_zones] if not test_zones.get("fire_points") else []
        else:
            no_fire_zones = []
        
        if no_fire_zones:
            import random
            selected_zone = random.choice(no_fire_zones)
            coordinates = selected_zone.get("coordinates", [])
            
            if coordinates and len(coordinates) >= 2:
                coords_array = coordinates if isinstance(coordinates[0], (list, tuple)) else [coordinates]
                xs = [c[0] for c in coords_array]
                ys = [c[1] for c in coords_array]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                
                new_fire_x = round(random.uniform(min_x, max_x), 3)
                new_fire_y = round(random.uniform(min_y, max_y), 3)
                new_fire_location = [new_fire_x, new_fire_y]
                
                # 从分配到该区域的无人机中选择发现者
                zone_id = selected_zone.get("id", "unknown_zone")
                uavs_in_zone = extract_uavs_in_zone(test_original_plan, zone_id)
                
                if uavs_in_zone:
                    all_uav_states = collect_uav_states()
                    zone_uav_states = [u for u in all_uav_states if u["id"] in uavs_in_zone]
                    surveillance_in_zone = [u for u in zone_uav_states if u["type"] == "surveillance_drone"]
                    random_uav = random.choice(surveillance_in_zone) if surveillance_in_zone else random.choice(zone_uav_states)
                else:
                    all_uav_states = collect_uav_states()
                    surveillance_uavs = [u for u in all_uav_states if u["type"] == "surveillance_drone"]
                    random_uav = random.choice(surveillance_uavs) if surveillance_uavs else random.choice(all_uav_states)
                
                test_fire_event = {
                    "location": new_fire_location,
                    "estimated_risk": "高",
                    "discovered_by": random_uav["id"],
                    "zone_id": selected_zone.get("id", "unknown_zone")
                }
                print(f"✓ 在区域 '{selected_zone.get('id')}' 中生成新火点: {new_fire_location}")
                print(f"✓ 发现者: {random_uav['id']}")
    
    # 如果仍然失败，使用默认值
    if not test_fire_event:
        print("⚠️ 无法从 zones 数据中生成新火点，使用默认值")
        
    success, code = execute_replan(test_zones, test_original_plan, test_fire_event)
    
    if success:
        print("\n" + "=" * 60)
        print("【测试结果】")
        print("=" * 60)
        print("✓ 重规划成功")
        print(f"\n新的任务分配:\n{code}")
    else:
        print("\n" + "=" * 60)
        print("【测试结果】")
        print("=" * 60)
        print("✗ 重规划失败")



if __name__ == "__main__":
    # 测试用例
    print("动态重规划模块 - 功能测试")
    print("=" * 60)
    
    # 从 zones_data.json 和 missions_plan.json 读取测试数据
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    zones_json_path = os.path.join(base_dir, "out", "zones_data.json")
    missions_json_path = os.path.join(base_dir, "out", "missions_plan.json")
    
    # 如果 zones_data.json 存在，从文件读取；否则使用默认硬编码数据
    if os.path.exists(zones_json_path):
        print(f"✓ 读取 zones_data.json: {zones_json_path}")
        with open(zones_json_path, 'r', encoding='utf-8') as f:
            all_zones_data = json.load(f)
        
        # 获取第一个图片的区域数据作为测试数据
        # 获取 zones_data.json 中的第一个图片名
        first_file = list(all_zones_data.keys())[0]
        # 使用这个图片名获取对应的区域数据
        test_zones = all_zones_data[first_file]
        print(f"✓ 已加载第一张图片数据: {first_file}")
        
        # 读取对应的任务分配计划
        if os.path.exists(missions_json_path):
            print(f"✓ 读取 missions_plan.json: {missions_json_path}")
            with open(missions_json_path, 'r', encoding='utf-8') as f:
                all_missions_data = json.load(f)
            # 用相同的图片名 first_file 从 missions_plan.json 查找任务分配
            if first_file in all_missions_data and all_missions_data[first_file]:
                mission_lines = all_missions_data[first_file]

                # 获取对应的任务分配计划字符串
                test_original_plan = "\n    ".join(mission_lines) if isinstance(mission_lines, list) else mission_lines
                print(f"✓ 已加载对应的任务分配计划")
            else:
                print(f"⚠️ 未在 missions_plan.json 中找到对应的数据，使用默认计划")               
        else:
            print(f"⚠️ 未找到 missions_plan.json ({missions_json_path})，使用默认计划")        
    else:
        print(f"⚠️ 未找到 zones_data.json ({zones_json_path})，使用默认硬编码数据")

    # 生成新火点事件 - 从监测区（Monitor）中发现新火点
    print("\n>>> 生成新火点事件")
    test_fire_event = None
    
    # 从 test_zones 中查找监测区域（Monitor 区域 - 没有火点的监控区域）
    if isinstance(test_zones, list):
        print(f"✓ zones数据是列表，共 {len(test_zones)} 个区域")
        # 调试：打印所有区域的类型
        for i, zone in enumerate(test_zones):
            risk = zone.get("risk_level", "unknown")
            zone_id = zone.get("id", f"zone_{i}")
            fire_points = zone.get("fire_points", [])
            print(f"  [{i}] {zone_id}: risk_level={risk}, fire_points={len(fire_points) if isinstance(fire_points, list) else 'N/A'}")
        
        monitor_zones = [zone for zone in test_zones 
                        if zone.get("risk_level") == "Monitor" 
                        and not zone.get("fire_points")]
        print(f"  → 找到 {len(monitor_zones)} 个 Monitor 类型的监测区域")
    elif isinstance(test_zones, dict):
        print("✓ zones数据是字典")
        monitor_zones = [test_zones] if (test_zones.get("risk_level") == "Monitor" 
                                         and not test_zones.get("fire_points")) else []
    else:
        print(f"⚠️ zones数据类型未知: {type(test_zones)}")
        monitor_zones = []
    
    if monitor_zones:
        # 从监测区域中选择一个【确保该区域有无人机被分配】
        import random
        valid_zones = []
        
        print(f"  → 检查 {len(monitor_zones)} 个监测区域是否有无人机分配...")
        
        # 筛选出确实有无人机分配的监测区域
        for zone in monitor_zones:
            zone_id = zone.get("id", "")
            print(f"    检查区域: {zone_id}")
            print(f"      原始计划片段: {test_original_plan[:200]}...")  # 调试：看计划内容
            uavs_in_zone = extract_uavs_in_zone(test_original_plan, zone_id)
            print(f"      → 找到无人机: {uavs_in_zone}")
            if uavs_in_zone:
                valid_zones.append((zone, uavs_in_zone))
        
        if not valid_zones:
            print("⚠️ 没有找到有无人机被分配的监测区域，尝试从无火点的区域中生成")
            monitor_zones = []
        else:
            selected_zone, zone_uav_ids = random.choice(valid_zones)
            coordinates = selected_zone.get("coordinates", [])
            
            # 获取该区域被分配的无人机的实时状态
            all_uav_states = collect_uav_states()
            zone_uav_states = [u for u in all_uav_states if u["id"] in zone_uav_ids]
        
        if monitor_zones and coordinates and len(coordinates) >= 2:
            # 计算坐标范围的中心
            coords_array = coordinates if isinstance(coordinates[0], (list, tuple)) else [coordinates]
            xs = [c[0] for c in coords_array]
            ys = [c[1] for c in coords_array]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            # 在监测区域内随机生成新火点
            new_fire_x = round(random.uniform(min_x, max_x), 3)
            new_fire_y = round(random.uniform(min_y, max_y), 3)
            new_fire_location = [new_fire_x, new_fire_y]
            
            # 从该区域被分配的无人机中选择发现者
            # 优先选择侦察型无人机（surveillance_drone）
            surveillance_in_zone = [u for u in zone_uav_states if u["type"] == "surveillance_drone"]
            random_uav = random.choice(surveillance_in_zone) if surveillance_in_zone else random.choice(zone_uav_states)
            
            test_fire_event = {
                "location": new_fire_location,
                "estimated_risk": "高",  # 新发现的火点默认标记为"高"风险
                "discovered_by": random_uav["id"],
                "zone_id": selected_zone.get("id", "unknown_zone"),
                "description": f"在监测区 '{selected_zone.get('id')}' 中新发现火情"
            }
            print(f"✓ 在监测区 '{selected_zone.get('id')}' 中发现新火点: {new_fire_location}")
            print(f"✓ 发现者: {random_uav['id']} ({random_uav['type']})")
    else:
        print("⚠️ 未找到监测区域，尝试从无火点的区域中生成")
        # 降级：从没有火点的任何区域中生成
        if isinstance(test_zones, list):
            no_fire_zones = [zone for zone in test_zones 
                            if not zone.get("fire_points")]
        elif isinstance(test_zones, dict):
            no_fire_zones = [test_zones] if not test_zones.get("fire_points") else []
        else:
            no_fire_zones = []
        
        if no_fire_zones:
            import random
            selected_zone = random.choice(no_fire_zones)
            coordinates = selected_zone.get("coordinates", [])
            
            if coordinates and len(coordinates) >= 2:
                coords_array = coordinates if isinstance(coordinates[0], (list, tuple)) else [coordinates]
                xs = [c[0] for c in coords_array]
                ys = [c[1] for c in coords_array]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                
                new_fire_x = round(random.uniform(min_x, max_x), 3)
                new_fire_y = round(random.uniform(min_y, max_y), 3)
                new_fire_location = [new_fire_x, new_fire_y]
                
                # 从分配到该区域的无人机中选择发现者
                zone_id = selected_zone.get("id", "unknown_zone")
                uavs_in_zone = extract_uavs_in_zone(test_original_plan, zone_id)
                
                if uavs_in_zone:
                    all_uav_states = collect_uav_states()
                    zone_uav_states = [u for u in all_uav_states if u["id"] in uavs_in_zone]
                    surveillance_in_zone = [u for u in zone_uav_states if u["type"] == "surveillance_drone"]
                    random_uav = random.choice(surveillance_in_zone) if surveillance_in_zone else random.choice(zone_uav_states)
                else:
                    all_uav_states = collect_uav_states()
                    surveillance_uavs = [u for u in all_uav_states if u["type"] == "surveillance_drone"]
                    random_uav = random.choice(surveillance_uavs) if surveillance_uavs else random.choice(all_uav_states)
                
                test_fire_event = {
                    "location": new_fire_location,
                    "estimated_risk": "高",
                    "discovered_by": random_uav["id"],
                    "zone_id": selected_zone.get("id", "unknown_zone")
                }
                print(f"✓ 在区域 '{selected_zone.get('id')}' 中生成新火点: {new_fire_location}")
                print(f"✓ 发现者: {random_uav['id']}")
    
    # 如果仍然失败，使用默认值
    if not test_fire_event:
        print("⚠️ 无法从 zones 数据中生成新火点，使用默认值")
        
    success, code = execute_replan(test_zones, test_original_plan, test_fire_event)
    
    if success:
        print("\n" + "=" * 60)
        print("【测试结果】")
        print("=" * 60)
        print("✓ 重规划成功")
        print(f"\n新的任务分配:\n{code}")
    else:
        print("\n" + "=" * 60)
        print("【测试结果】")
        print("=" * 60)
        print("✗ 重规划失败")
