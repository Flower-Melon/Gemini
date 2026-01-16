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

def get_uav_resources(module):
    """提取模块中所有 UAV 定义"""
    uavs = []
    for name, obj in inspect.getmembers(module):
        # 假设所有以 UAV_ 开头的变量都是无人机配置字典
        if name.startswith("UAV_") and isinstance(obj, dict):
            uavs.append(f"{name} = {json.dumps(obj, ensure_ascii=False)}")
    return "\n".join(uavs)

def get_few_shot_examples():
    """提供少样本示例 (Few-Shot Prompting)，教会模型如何正确使用函数"""
    return """
# 示例 1: 简单的单机搜索任务
# 输入: 区域 "Zone 1" 需要 1 架无人机
SearchArea(['UAV_01'], [[0.0, 0.0], [0.2, 0.0], [0.2, 0.2], [0.0, 0.2]])

# 示例 2: 复杂的多机协同搜索
# 输入: 区域 "Zone 2" 需要 3 架无人机
SearchArea(['UAV_02', 'UAV_03', 'UAV_04'], [[0.5, 0.5], [0.8, 0.5], [0.8, 0.8], [0.6, 0.9], [0.5, 0.8]])
"""

# 构建动态提示词
def create_command_prompt(zones):
    # 1. 获取技能库（函数定义）
    skills_context = get_function_definitions(function)
    
    # 2. 获取无人机资源
    uav_context = get_uav_resources(UAV)
    
    # 3. 获取少样本示例
    examples_context = get_few_shot_examples()
    
    # 4. 序列化任务区域数据
    zones_json = json.dumps(zones, ensure_ascii=False, indent=2)
    
    prompt = f"""
你是一名无人机集群指挥官（Commander）。你的任务是根据**现有资源**和**任务区域信息**，调用**技能函数库**中的函数来完成任务分配。
目前所有无人机都在基地，不用使用GetAllUAVStatus()获取状态信息
==================================================
【1. 可用无人机资源】
==================================================
{uav_context}

==================================================
【2. 技能函数库 (SDK)】
==================================================
以下是你可调用的所有函数及其定义（请仔细阅读文档字符串以了解参数约束）：

{skills_context}

==================================================
【3. 函数调用示例 (Few-Shot)】
==================================================
请严格模仿以下代码风格进行输出：
{examples_context}

==================================================
【4. 任务区域情报 (JSON)】
==================================================
{zones_json}

==================================================
【5. 指令生成要求 (CRITICAL)】
==================================================
1. **任务分配原则**：
   - 根据 zones_json 中每个区域的 `uav_count` 字段分配相应数量的无人机。
   - **资源互斥**：每架无人机（UAV_xx）只能被分配一次，严禁重复使用。
   - 优先使用 `SearchArea` 函数进行区域搜索任务。
   - **智能决策**：如果函数库中有其他适用的函数（如发现火点需要标记、或者需要投放灭火弹等），请根据区域描述（`reason` 或 `type`）灵活决策是否需要调用。例如，如果是简单的搜索任务，主要用 `SearchArea`。
   
2. **输出格式**：
   - 请直接输出 Python 代码。
   - 不要输出 markdown 标记（如 ```python ）。
   - 不要输出任何解释性文字。
   - 代码中只需包含函数调用。

==================================================
【6. 生成的指令代码】
==================================================
"""
    return prompt