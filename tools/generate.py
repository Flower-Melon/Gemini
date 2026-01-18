"""
生成无人机指挥官的动态提示词（Command Prompt）
包含：
1. 技能库（函数定义）
2. 可用无人机资源
3. 少样本示例 (Few-Shot Prompting)
"""
import json
import inspect

# 导入用户的数据文件
import data.function as function
import data.UAV as UAV

def get_function_definitions(module):
    """提取模块中所有函数的源代码作为提示词上下文"""
    definitions = []
    # 获取模块中所有的成员
    for name, obj in inspect.getmembers(module):
        # 只提取函数，且不包含内部函数（以_开头的）
        if inspect.isfunction(obj) and not name.startswith("_"):
            try:
                # 获取源代码（包含文档字符串）
                source = inspect.getsource(obj)
                definitions.append(source)
            except OSError:
                pass
    return "\n\n".join(definitions)

def get_uav_status_definition(module):
    """提取状态常量的定义，帮助 LLM 理解状态的含义"""
    for name, obj in inspect.getmembers(module):
        if name == "UAVStatus" and inspect.isclass(obj):
            return inspect.getsource(obj)
    return ""

def get_uav_resources(module):
    """提取模块中所有 UAV 定义"""
    uavs = []
    for name, obj in inspect.getmembers(module):
        # 假设所有以 UAV_ 开头的变量都是无人机配置字典
        if name.startswith("UAV_") and isinstance(obj, dict):
            uavs.append(f"{name} = {json.dumps(obj, ensure_ascii=False)}")
    return "\n".join(uavs)

def get_few_shot_examples():
    """提供纯净的少样本示例 (展示多机轮询调度)"""
    return """
    zone_1_uavs = ['UAV_01', 'UAV_02']                                          
    SearchArea(zone_1_uavs, 'Zone_1')
    FlyToFire(zone_1_uavs[0], [0.15, 0.25]) 
    FlyToFire(zone_1_uavs[1], [0.18, 0.28]) 
    FlyToFire(zone_1_uavs[0], [0.19, 0.30])

    zone_2_uavs = ['UAV_04']
    SearchArea(zone_2_uavs, 'Zone_2')
    FlyToFire(zone_2_uavs[0], [0.66, 0.77])
    FlyToFire(zone_2_uavs[0], [0.68, 0.79])
    """

# 构建动态提示词
def create_command_prompt(zones):

    # skills_context = get_function_definitions(function)

    # 1. 获取状态定义
    status_def = get_uav_status_definition(UAV)
    
    # 2. 获取无人机资源
    uav_context = get_uav_resources(UAV)
      
    # 3. 序列化任务区域数据
    zones_json = json.dumps(zones, ensure_ascii=False, indent=2)
    
    # 4. 获取少样本示例
    examples_context = get_few_shot_examples()
    
    prompt = f"""
    你是一名无人机集群指挥官。面对复杂的战场环境，你需要执行**“全局资源规划 -> 战术动作生成”**的决策流程。

    ==================================================
    【1. 核心决策法则 (STRICT LOGIC flow)】
    ==================================================
    你生成的代码必须严格遵循以下逻辑流：

    **阶段一：全局资源规划 (Resource Planning)**
    1. **优先级排序**：
    - 第一梯队：包含 `fire_points` (火点) 的高危区域。
    - 第二梯队：仅需 `Search` 的普通区域。
    2. **能力匹配 (Capability Matching)**：
    - **高危区域**：必须优先分配 `extinguishing_drone` (灭火机)，且优先选择 `current_payload > 0` 的机组。
    - **普通区域**：优先分配 `surveillance_drone` (侦查机)，若不足才使用闲置的灭火机。
    3. **最小生存保障 (Minimum Guarantee)**：
    - **原则**：优先确保每个区域至少分配 1 架 UAV。
    - **流程**：先给所有区域各分 1 架 -> 剩余兵力再分给高危区域。
    4. **全局互斥**：每架 UAV 全局只能被使用一次。

    **阶段二：空值熔断检测 (Critical Check)**
    对于每一个任务区域：
    1. 获取阶段一分配给该区域的 UAV 列表。
    2. ⚠️ **熔断规则**：
    - 如果列表为空 (`[]`)，**严禁生成任何代码**！
    - 直接静默跳过该区域，**不要**输出 `zone_x_uavs = []`，**不要**输出任何注释。

    **阶段三：战术动作生成 (Action Generation)**
    仅对通过熔断检测（列表非空）的区域生成代码：
    1. **变量定义**：必须先定义 `zone_x_uavs = [...]`。
    2. **搜寻任务**：调用 `SearchArea(zone_x_uavs, 'zone_id')` (传入整个列表)。
    3. **灭火任务 (Fire Engagement)**：
    - 遍历该区域内的所有 `fire_points`。
    - **载荷饱和策略 (Payload Saturation Strategy)**：
        - 不要轮询！不要平均分配！
        - **逻辑**：始终优先使用列表中的第一架可用灭火机。
        - **计数**：统计该机已分配的 `FlyToFire` 次数。当次数达到其 `current_payload` 上限时，视为弹药耗尽，立即切换到列表中的下一架灭火机。
        - **剔除**：严禁使用 `surveillance_drone` 或 `current_payload == 0` 的无人机执行灭火。
    - **指令格式**：`FlyToFire(zone_x_uavs[i], [x, y])` (必须使用列表索引指定单机)。

    ==================================================
    【2. 状态与资源】
    ==================================================
    **可用性定义**：
    {status_def}
    - 仅 `IDLE` 或 `RETURN`(电量>50%) 的无人机可被分配。

    **当前资源池**：
    {uav_context}

    ==================================================
    【3. 任务区域情报 (JSON)】
    ==================================================
    {zones_json}

    ==================================================
    【4. 代码生成规范 (Syntax Constraints)】
    ==================================================
    1. **纯净代码**：严禁输出注释、Markdown 标记、print 语句。
    2. **变量绑定**：严格遵守 `变量定义 -> 函数调用` 的顺序。
    3. **索引引用**：灭火时必须使用 `zone_x_uavs[i]`，禁止直接使用字符串 ID。

    ==================================================
    【5. 语法格式参考 (Syntax Only)】
    ==================================================
    以下示例仅用于展示**代码格式**，**不要**参考其中的分配逻辑（逻辑请严格遵守上文的【核心决策法则】）：
    {examples_context}

    ==================================================
    【6. 最终指令生成】
    ==================================================
    基于上述法则，输出最终 Python 代码：
    """
    return prompt